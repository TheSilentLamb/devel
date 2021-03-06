import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from threading import Thread
from time import sleep
from time import time

class FuturesTrade(webdriver.Chrome):
    def __init__(self, client, driver_exe=r'C:\Users\tai.tv\Desktop\Automation\chromedriver_win32\chromedriver.exe'):
        self.client = client
        self.driver_exe = driver_exe
        self.website = r'https://fut.masvn.com/login.do?redirect=/wts/view/tradingFOS.do'
        
        try:
            webdriver.Chrome.__init__(self, self.driver_exe)
        except:
            raise ValueError('Can\'t launch the web driver with the given .exe file')
    

    def load_website(self):
        self.delete_all_cookies()
        self.implicitly_wait(20)
        self.get(self.website)

        return
    

    def login(self):
        try:
            # Login
            username_input = self.find_element_by_id('mvClientID')
            password_input = self.find_element_by_id('mvPassword')
            captcha = self.find_element_by_id('mainCaptcha')
            captcha_input = self.find_element_by_id('securitycode')
            login_button = self.find_element_by_id('loginOn')

            captcha_text = captcha.text.replace(' ', '')

            username_input.clear()
            password_input.clear()
            captcha_input.clear()
            username_input.send_keys(str(self.client['username']))
            password_input.send_keys(str(self.client['password']))
            captcha_input.send_keys(captcha_text)
            login_button.click()

            # Verify client
            self._verify_client()
        
        except:
            sleep(0.5)
            self.login()

        return
    

    def show_status(self):
        status_table = self._get_status_table()
        columns = [6, 7, 8, 9, 10, 11, 12, 13, 14, 22]
        col_name = [
            'Mã HĐ',
            'Mua/Bán',
            'Giá',
            'Khối lượng',
            'KL còn lại',
            'KL khớp',
            'Giá TB',
            'Trạng thái',
            'Loại lệnh',
            'Thời gian GD'
        ]
        result_table = status_table.iloc[:, columns]
        result_table.columns = col_name

        print('-' * 80)
        print('Client:', self.client["name"])
        print(result_table)
        print('-' * 80, end='\n\n')

        return result_table
    

    def entry_order(self, entry_strategies, wait=10):
        self.entry_strategies = entry_strategies
        stoploss_strategies = self._set_exit_strategies()
        
        for contract in self.entry_strategies:
            try:
                self.place_single_order(
                    contract,
                    self.entry_strategies[contract]['direction'],
                    self.entry_strategies[contract]['volume'],
                    self.entry_strategies[contract]['tolerance']
                )
                
                # Verify client
                self._verify_client()

                # Update status
                self.entry_strategies[contract]['status'] = self.check_status(
                    contract,
                    self.entry_strategies[contract]['direction']
                )

            except Exception as e:
                self.entry_strategies[contract]['status'] = 'Failed'
                print(f'{self.client["name"]} - {self.client["username"]} - '
                      f'Could not place {entry_strategies[contract]["direction"]} order for {contract}. '
                      f'Error message: {e}')
                pass
            
            if stoploss_strategies['order_stoploss'] and stoploss_strategies['trigger_stoploss']:
                try:
                    self.place_single_stoploss(
                        contract,
                        stoploss_strategies[contract]['direction'],
                        stoploss_strategies[contract]['volume'],
                        stoploss_strategies[contract]['order_stoploss'],
                        stoploss_strategies[contract]['trigger_stoploss']
                    )
                except Exception as e:
                    self.entry_strategies[contract]['stoploss_status'] = 'Failed'
                    print(f'{self.client["name"]} - {self.client["username"]} - '
                          f'Could not place stop loss order for {contract}. '
                          f'Error message: {e}')
                    pass
        
        sleep(wait)
        self.cancel_order()

        return
    

    def exit_order(self, exit_strategies):
        exit_strategies = self._set_exit_strategies(exit_strategies)
        
        for contract in exit_strategies:            
            try:
                self.place_single_order(
                    contract,
                    exit_strategies[contract]['direction'],
                    exit_strategies[contract]['volume'],
                    exit_strategies[contract]['tolerance']
                )
            except Exception as e:
                print(f'{self.client["name"]} - {self.client["username"]} - '
                      f'Could not place {exit_strategies[contract]["direction"]} order for {contract}. '
                      f'Error message: {e}')
                continue
        
        return
    

    def cancel_order(self):
        for contract in self.entry_strategies:
            direction = self.entry_strategies['direction']
            self.cancel_single_order(contract, direction)
            print(f'{self.client["name"]} - {self.client["username"]} - '
                  f'Entry order for contract {contract} is canceled '
                  f'because of being unable to be filled.')
        
        return

    
    def place_stoploss(self, stoploss_strategies={}):
        stoploss_strategies = self._set_exit_strategies(stoploss_strategies)
        
        for contract in stoploss_strategies:
            try:
                # Cancel previous stoploss order if any
                try:
                    self.cancel_single_order(contract, stoploss_strategies[contract]['direction'])
                except:
                    pass
                
                # Place stoploss order
                self.place_single_stoploss(
                    contract,
                    stoploss_strategies[contract]['direction'],
                    stoploss_strategies[contract]['volume'],
                    stoploss_strategies[contract]['order_stoploss'],
                    stoploss_strategies[contract]['trigger_stoploss']
                )
            
            except Exception as e:
                self.entry_strategies[contract]['stoploss_status'] = 'Failed'
                print(f'{self.client["name"]} - {self.client["username"]} - '
                      f'Could not place stop loss order for {contract}. Error message: {e}')
                continue
        
        return


    def place_single_order(self, contract, direction, volume, tolerance=0.3):
        self.refresh()
        
        # Unlock button
        self._unlock_button(contract)
        
        # Input volume
        self._input_volume(contract, volume)

        # Set tolerance
        self._set_tolerance(contract, tolerance)

        # Place order
        self._proceed_order(contract, direction)
        
        # Select market order type -- Incomplete development
        # self._select_market_order_type(market_order_type)

        sleep(0.5)
        
        return self.check_status(contract, direction)

    
    def place_single_stoploss(self, contract, direction, volume, order_stoploss, trigger_stoploss):
        self.refresh()

        # Check status
        status = self.check_status(contract, direction)
        
        if status == 'Matched':

            # Check which type of stop loss to go with
            if direction == 'short':
                stoploss_order = self.find_element_by_id('sTab')
                action_button = self.find_element_by_id('enterSell')
            elif direction == 'long':
                stoploss_order = self.find_element_by_id('bTab')
                action_button = self.find_element_by_id('enterBuy')
            else:
                raise ValueError(f'{self.client["name"]} - {self.client["username"]} - '
                                 'Direction must be either long or short')
            
            stoploss_order.click()

            # Place stop loss
            condition_box = self.find_element_by_id('bOrderConChk')
            stoploss_contract = self.find_element_by_id('bStockID')
            volume_input = self.find_element_by_id('bVolume')
            order_stoploss_input = self.find_element_by_id('bPrice')
            trigger_stoploss_input = self.find_element_by_id('bPriceCon')

            if not condition_box.is_selected():
                condition_box.click()
            
            stoploss_contract.clear()
            volume_input.clear()
            order_stoploss_input.clear()
            trigger_stoploss_input.clear()

            stoploss_contract.send_keys(str(contract))
            volume_input.send_keys(str(volume))
            order_stoploss_input.send_keys(str(order_stoploss))
            trigger_stoploss_input.send_keys(str(trigger_stoploss))

            action_button.click()
        
        else:
            print(f'{self.client["name"]} - {self.client["username"]} - '
                  f'Could not place a stop loss because the {direction} '
                   'order has not been filled yet')

        return
    

    def cancel_single_order(self, contract, direction):
        status = self.check_status(contract, direction)
        
        if status == 'Pending':
            status_table = self._get_status_table()
            contract_index = self._get_contract_index(status_table, contract, direction)
            contract_index += 1
            button_xpath = f'//*[@id="grdTodayHis"]/tr[{contract_index}]/td[3]/button'
            cancel_button = self.find_element_by_xpath(button_xpath)
            cancel_button.click()

            sleep(0.01)
            
            confirm_button = self.find_element_by_id('cmBtnConfirmed')
            confirm_button.click()

        return
    

    def check_status(self, contract, direction):
        self.refresh()
        sleep(0.1)

        try:
            status_table = self._get_status_table()
            contract_index = self._get_contract_index(status_table, contract, direction)
            status = status_table.iloc[contract_index, 13]
            status = status.replace(' ', '')

            if status == 'Khớp':
                status = 'Matched'
            elif status == 'Hủy':
                status = 'Canceled'
            else:
                status = 'Pending'
        
        except Exception as e:
            print(f'{self.client["name"]} - {self.client["username"]} - {e}')
            status = 'Error'
                
        return status
    

    def reload_entry_strategies(self, entry_strategies):
        self.entry_strategies = entry_strategies

        return
    

    def update_client_info(self, client_info):
        self.client = client_info

        return
    

    def _get_contract_index(self, status_table, contract, direction):
        try:
            contract_verification = status_table.iloc[:, 6].str.replace(' ', '') == contract
            direction_verification = status_table.iloc[:, 7].str.replace(' ', '') == direction
            final_verification = contract_verification & direction_verification
            contract_index = final_verification[final_verification is True].index[0]
        except:
            msg = f'Could not find contract {contract} in list of current trades'
            raise ValueError(msg)
        
        return contract_index
    

    def _get_status_table(self, attempts=3):
        try:
            page_source = self.page_source
            status_table = pd.read_html(page_source)[6]

            return status_table
        
        except Exception as e:
            if attempts >= 0:
                sleep(0.1)
                self._get_status_table(attempts-1)
            else:
                raise ValueError(e)
    

    # def _select_market_order_type(self, market_order_type): # Incomplete development
    #     select = Select(self.find_element_by_id('bType'))
    #     select.select_by_visible_text(market_order_type)

    #     return
    

    def _proceed_order(self, contract, direction):
        if direction == 'long':
            execution_button = self.find_element_by_xpath(f'//*[@id="srow_{contract}"]/table/tbody/tr[2]/td[1]')
        elif direction == 'short':
            execution_button = self.find_element_by_xpath(f'//*[@id="srow_{contract}"]/table/tbody/tr[2]/td[4]')
        else:
            raise ValueError(f'{self.client["name"]} - {self.client["username"]} - '
                             'Direction must be either long or short')
        
        execution_button.click()

        return
    

    def _set_exit_strategies(self, exit_strategies={}):
        if not exit_strategies:
            exit_strategies = self.entry_strategies.copy()
        
        for contract in exit_strategies:
            # Identify direction of the stoploss order
            if self.entry_strategies[contract]['direction'] == 'long':
                exit_strategies[contract]['direction'] = 'short'
            elif self.entry_strategies[contract]['direction'] == 'short':
                exit_strategies[contract]['direction'] = 'long'
            
            # Adopt volume from entry_strategies
            if 'volume' not in exit_strategies[contract]:
                exit_strategies[contract]['volume'] = self.entry_strategies[contract]['volume'].copy()
        
        return exit_strategies
    

    def _set_tolerance(self, contract, tolerance):
        slippage = self.find_element_by_xpath(f'//*[@id="ampli_{contract}"]')
        slippage.clear()
        slippage.send_keys(str(tolerance))

        return
    

    def _input_volume(self, contract, volume):
        volume_input = self.find_element_by_id(f'vol_{contract}')
        volume_input.clear()
        volume_input.send_keys(str(volume))

        return
    

    def _unlock_button(self, contract):
        unlock_button = self.find_element_by_id(f'locked_{contract}')
        try:
            unlock_button.click()
        except:
            pass

        return


    def _verify_client(self):
        confirm_button = WebDriverWait(self, 5).until(
            EC.presence_of_element_located((By.ID, 'btnAuthConfirm'))
        )
        
        matrix1 = self.find_element_by_id('mvWordMatrixKey01')
        matrix2 = self.find_element_by_id('mvWordMatrixKey02')
        first_digit_input = self.find_element_by_id('wordMatrixValue01')
        second_digit_input = self.find_element_by_id('wordMatrixValue02')
        

        matrix1 = matrix1.text.split(',')
        matrix2 = matrix2.text.split(',')
        first_digit = self.client['clientcard'].loc[int(matrix1[0]), matrix1[1]]
        second_digit = self.client['clientcard'].loc[int(matrix2[0]), matrix2[1]]

        first_digit_input.clear()
        first_digit_input.send_keys(first_digit)
        second_digit_input.clear()
        second_digit_input.send_keys(second_digit)

        confirm_button.click()

        return


class MultiAccTrade():
    def __init__(self, clients):
        self.accounts = self._initiate(clients)
        self.workers = len(clients)
    
    
    def _initiate(self, clients):
        accounts = {}
        for client in clients:
            accounts[client] = FuturesTrade(clients[client])
        
        return accounts
    
    
    def login(self):
        self._run_multithreads('login')
        
        return
    

    def show_status(self):
        self._run_multithreads('show_status')

        return
    
    
    def entry_order(self, entry_strategies):
        self._run_multithreads('entry', entry_strategies)
        
        return
    

    def cancel_order(self):
        self._run_multithreads('cancel')

        return
    
    
    def exit_order(self, exit_strategies):
        self._run_multithreads('exit', exit_strategies)
        
        return
    
    
    def place_stoploss(self, stoploss_strategies={}):
        self._run_multithreads('stoploss', stoploss_strategies)
        
        return
    
    
    def close(self):
        self._run_multithreads('close')

        return
    

    def reload_entry_strategies(self, entry_strategies):
        self._run_multithreads('reload_strategies', entry_strategies)
                
        return
    

    def update_client_info(self, client_info):
        self._run_multithreads('update_client', client_info)

        return
    

    def _run_multithreads(self, *args):
        threads = {}
        
        for account in self.accounts:
            threads[account] = Thread(
                target=self._run_instance_method,
                args=(self.accounts[account], *args)
            )

        for account in self.accounts:
            threads[account].start()

        for account in self.accounts:
            threads[account].join()
    
    
    def _run_instance_method(self, instance, method, *args):
        if method == 'login':
            instance.load_website()
            instance.login()
        elif method == 'show_status':
            instance.show_status(*args)
        elif method == 'entry':
            instance.entry_order(*args)
        elif method == 'exit':
            instance.exit_order(*args)
        elif method == 'stoploss':
            instance.place_stoploss(*args)
        elif method == 'cancel':
            instance.entry_order(*args)
        elif method == 'close':
            instance.close()
        elif method == 'reload_strategies':
            instance.reload_entry_strategies(*args)
        elif method == 'update_client':
            instance.update_client_info(*args)
        
        return
