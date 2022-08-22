#!/usr/local/bin/python3
#vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
-----------------------------------------------------------------------

 Simple Infoblox B1DDI DNS Context Switcher Demo for CNAME records
 Uses the following Tags associated with the CNAME records:
    Service:    service name, e.g. (mail, intranet, www)
    Context_state: normal, backup, manual
    Primary_server: Canonical name associated with normal state
    Backup_server: Canonical name of associated with backup state

 Requirements:
   Python 3.7+

 Usage: <scriptname> [options]
        -h        help
        -v        verbose


 Author: Chris Marrison
 Email: chris@infoblox.com

 ChangeLog:
   20220822 v2.0    Ported original concept from NIOS to BloxOne DDI

 Todo:

 Copyright 2022 Chris Marrison / Infoblox Inc

 Redistribution and use in source and binary forms,
 with or without modification, are permitted provided
 that the following conditions are met:

 1. Redistributions of source code must retain the above copyright
 notice, this list of conditions and the following disclaimer.

 2. Redistributions in binary form must reproduce the above copyright
 notice, this list of conditions and the following disclaimer in the
 documentation and/or other materials provided with the distribution.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 POSSIBILITY OF SUCH DAMAGE.
----------------------------------------------------------------------
"""

__version__ = '2.0'
__author__ = 'Chris Marrison'
__email__ = 'chris@infoblox.com'
__license__ = 'BSD2'

import bloxone
import os
import logging
import json
import yaml
import argparse

### Classes ###

class DNS_CONTEXT(bloxone.b1ddi):
    '''
    B1DDI DNS Context Class
    '''
    def __init__(self, cfg_file='config.ini', services='services.yml'):
        '''
        Call base __init__ and extend
        '''
        super().__init__(cfg_file)

        self.services = {}

        # Check for yaml file and raise exception if not found
        if os.path.isfile(services):
            # Read yaml configuration file
            try:
                self.services = yaml.safe_load(open(services, 'r'))
            except yaml.YAMLError as err:
                logging.error(err)
                raise
        else:
            logging.error(f'No such file {services}')
            raise FileNotFoundError(f'YAML config file "{services}" not found.')

        # Instantiate b1ddi class
        # self.b1app = b1ddi(cfg_file) 

        return


    def normalise_cname(self, record):
        '''
        Normalise CNAME to FQDN

        Parameters:
            record (dict): Record data
        
        Returns:
            cname (str): Fully qualified Canonical Name
        '''
        cname = ''
        # Check record type and continue
        if record.get('type') == 'CNAME':
            cname = record['rdata']['cname']
            # Check for FQDN
            if cname[-1:] != '.':
                # Append zone name to fully qualify
                cname += f'.{record.get("absolute_zone_name")}'
        else:
            cname = None
        
        return cname


    def getcontext(self, service):
        '''
            Get current context of service

            Returns
                id:       WAPI object iderence
                name:      Resource record name
                cname:     Canonical name
                state:     Current context State
                primary:   Canonical name for state normal
                backup:    Canonical name for state backup

        '''
        state = {}
        name = ''
        tags = {}
        primary = ''
        backup = ''
        context = ''
        fields = 'name_in_zone,absolute_name_spec,absolute_zone_name,rdata,id,tags,type'
        filter = 'type=="CNAME"'
        tfilter = f'Service=="{service}"'

        # WAPI call GET / CNAME
        response = self.get('/dns/record', 
                            _fields=fields,
                            _filter=filter, 
                            _tfilter=tfilter)

        # Check response and return "" on error or empty results
        if response.status_code in self.return_codes_ok:
            records = response.json()['results']
            for record in records:
                name = record.get('absolute_name_spec') 
                cname = self.normalise_cname(record)
                tags = record.get('tags')

                if 'Context_state' in tags.keys():
                    context = tags['Context_state']
                else:
                    context = 'Not configured.'

                if 'Primary_server' in tags.keys():
                    primary = tags['Primary_server']
                else:
                    primary = 'Not configured.'

                if 'Backup_server' in tags.keys():
                    backup = tags['Backup_server']
                else:
                    backup = 'Not configured.'

                state[name] = { 'id': record['id'],
                                'name': name,
                                'cname': cname,
                                'context': context,
                                'primary': primary,
                                'backup': backup }
        else:
            logging.error(f'{response.text}')
            state = None

        return state


    def checkcontext(self, record_state):
        '''
            Check context is correct for state

            Returns True or Falase
        '''
        context = False

        s = record_state
        if "Not configured." in s.values():
            context = False
        else:
            if s.get('context') == "normal" and s.get('cname') == s.get('primary'):
                context = True
            elif s.get('context') == "backup" and s.get('cname') == s.get('backup'):
                context = True
            elif s.get('context') == "manual":
                context = True
            else:
                context = False

        return context


    def reportcontext(self, service, state):
        '''
            Output Current State of Service
        '''
        # Check for records
        if state:
            # Check each record for correct context
            for r in state:
                rs = state[r]
                if self.checkcontext(rs):
                    print(f'Service: {service}, Record: {rs["name"]}, ' +
                           'Status check: OK: ')
                    print(f'Status: {rs["context"]}, ' +
                          f'CNAME: {rs["cname"]}, ' +
                          f'Primary: {rs["primary"]}, ' +
                          f'Backup: {rs["backup"]}')
                else:
                    print(f'Service: {service}, Record: {r}, ' +
                          f'Status check: FAILED:')
                    print(f'Status: {rs["context"]}, ' +
                          f'CNAME: {rs["cname"]}, ' +
                          f'Primary: {rs["primary"]}, ' +
                          f'Backup: {rs["backup"]}')
        else:
            print(f'Service: {service} has no records set up.')

        return


    def switch(self, record_state, newstate):
        '''
            Switch context using WAPI

            Returns
                success: True or False
                response.text: response text of wapi call
        '''
        success = False
        id = record_state.get('id')
        
        if newstate == "normal":
            newcname = record_state.get('primary')
        elif newstate == "backup":
            newcname = record_state.get('backup')
        elif newstate == "manual":
            print('Currently not implemented')
            newcname = None
            success = True
        else:
            logging.error(f'State {newstate} not supported')
            success = False
            rtext = self._not_found_response

        if newcname:
            # API call to update CNAME
            tags = self.get_tags(f'/{id}')
            if tags:
                tags['tags'].update({ "Context_state": newstate })
                body = { 'rdata': { 'cname': newcname } }
                body.update(tags)
            else:
                logging.error('Failed to get existing tags')

            response = self.replace(f'/{id}', body=json.dumps(body))
            rtext = response.text

            # Check response and return "" on error or empty results
            if response.status_code in self.return_codes_ok:
                logging.debug(f'Record {id} updated to state {newstate}')
                success = True
            else:
                logging.error(response.text)
                success = False

        else:
            print(f'Switching Context_state to manual')
            tags = self.get_tags(f'/{id}')
            if tags:
                tags['tags'].update({ "Context_state": "manual" })
                response = self.replace(f'/{id}', body=json.dumps(tags))
                rtext = response.text
                if response.status_code in self.return_codes_ok:
                    success = True
                else:
                    logging.error(response.text)
                    success = False

        return success, rtext


    def switchcontext(self, service, newstate):
        '''
            Switch CNAME context

            Returns True or False
        '''
        complete = False
        success = False
        successful = []
        failed = []
        rtext = None
        # Get current context
        state = self.getcontext(service)

        # Check Context enabled records exist
        if state:
            # Check all records for correct context
            for r in state:
                record_state = state[r]
                if self.checkcontext(record_state):
                    currentstate = record_state.get('context')

                    if currentstate == newstate:
                        print(f'Requested state for record {r} ' +
                               'matches existing state: No change made.')
                        successful.append(r)
                    else:
                        print(f'Switching state for record {r}')

                        # Change to new state
                        success, rtext = self.switch(record_state, newstate)

                        # Check whether this was successful
                        if success:
                            successful.append(r)
                            print('Switched successful, new state:')
                            print()
                        else:
                            failed.append(r)
                            print('Update failed, please check for context.')
                            print(rtext)
                else:
                    print(f'Status check failed, for {r} please see details below:')
                    print()
                    print(f'Service: {service}, Record: {r}, ' +
                          f'Status check: FAILED: ' + 
                          f'Status: {record_state["context"]}, ' +
                          f'CNAME: {record_state["cname"]}, ' +
                          f'Primary: {record_state["primary"]}, ' +
                          f'Backup: {record_state["backup"]}')

			# Check for any failures and report
            if len(successful) == len(state):
                complete = True
                print(f'All records in state {newstate}')
                print('State health check:')
                state = self.getcontext(service)
                self.reportcontext(service, state)
            else:
                complete = False
                print('Some records failed to switch state:')
                print('Failure summary:')
                for r in failed:
                    print(r)
                
                print()
                print('Status check:')
                state = self.getcontext(service)
                self.reportcontext(service, state)
        else:
            print(f'Service: {service} has no records set up.')

        return complete

# *** Functions ***

def parseargs():
    """
    Parse Arguments Using argparse

        Returns arguments
    """
    parse = argparse.ArgumentParser(description='DNS Context Switcher')

    #parse.add_argument('-o', '--output', type=str, help="CSV Output to <filename>")
    #parse.add_argument('-s', '--silent', action='store_true', help="Silent mode")
    parse.add_argument('-s', '--service', type=str, default="all", help="Service Type")
    parse.add_argument('-S', '--state', type=str, default="get",
        choices=['get','normal','backup', 'manual'], help="Change or get service context")
    parse.add_argument('-c', '--config', type=str, default="bloxone.ini", help="Config file for bloxone")
    
    return parse.parse_args()


def main():
    '''
    Core Logic
    '''

    # Parse Arguments
    args = parseargs()
    service = args.service
    state = args.state
    config = args.config

    # Setup WAPI b1ddi
    context = DNS_CONTEXT(cfg_file=config)

    if service == "all" and state == "get":
        for srv in context.services['applications']:
            state = context.getcontext(srv)
            context.reportcontext(srv, state)

    elif state == "get":
        current_state = context.getcontext(service)
        context.reportcontext(service, current_state)

    else:
        context.switchcontext(service, state)
    
    return


### Main ###
if __name__ == '__main__':
    exitcode = main()
    exit(exitcode)
## End Main ###