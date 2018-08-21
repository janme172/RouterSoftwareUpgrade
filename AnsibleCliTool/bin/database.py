from __future__ import print_function
import os
import sys

import pyodbc
import MySQLdb
import pandas as pd

from collections import OrderedDict
import datetime

class Database(object):
    """
    This Class is used for handling different database operations.
    """
    __slots__ = ('server', 'db_type', 'database', 'user', 'password', 'connection', 'mgw_device_map')

    def __init__(self, server, db_type, database, user, password):
        self.server = server
        self.database = database
        self.db_type = db_type
        self.user = user
        self.password = password
        self.connection = None
        #self.mgw_device_map = self.pd_select(table='[CDR_SUMMARY_PROD].[dbo].[Port_Utilization_tbl]', cols=['device', 'mgwName'], distinct_rows=True)

    def connect(self):
        """
        This method is used for connecting to the Database.
        :return: it sets the connection attribute of the DB if successfully connected otherwise returns false.
        """
        # Check if connection already exists
        if self.connection:
            print("Error : Connection Already Exists !!!. Please disconnect first to reconnect.")
            return None
        # Create the connection string
        conn_str = None
        if str(self.db_type).lower() == 'mssql':
            conn_str = "Driver={{SQL Server}};Server={0.server};uid={0.user};pwd={0.password};Database={0.database};Trusted_Connection=yes;".format(self)

        try:
            # Connect to the Database specified in the connection string
            if str(self.db_type).lower() == 'mssql':
                if conn_str:
                    connection = pyodbc.connect(conn_str)
                else:
                    raise ValueError("Error: Connection String not found to connect to DB {}.".format(self.server))
            elif str(self.db_type).lower() == 'mysql':
                connection = MySQLdb.connect(host=self.server, user=self.user, passwd=self.password, db=self.database)

        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            print("Error: Unable to connect to Database '{0.database}' on Server '{0.server}'.\n{1}".format(self, e))
            return None
        else:
            # Set the connection
            self.connection = connection
            #print("Successfully connected to Database {0.database}@{0.server}.".format(self))
            return True

    def disconnect(self):
        # Check if there exists a connection to disconnect.
        if not self.connection:
            print("Error : No connection found to Disconnect.")
            return True
        try:
            # Close the connection
            self.connection.close()
        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            print("Error : Unable to disconnect from Database {0.database}@{0.server}.\n{1}".format(self, e))
            return False
        else:
            self.connection = None
            #print("Disconnected from Database {0.database}@{0.server} Successfully.".format(self))
            return True

    def execute(self, sql_cmd):
        #sql_cmd = "insert into [Devices_Inventory].[dbo].[device_version_info] (build_date, device_ip, ver_date) values ('2017-02-11', '172.30.149.78', '2017-06-02');"
        try:
            if not self.connection:
                raise RuntimeError("Error : Not Connected. Please connect first using connect().")
        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            return False

        # Create the Cursor to execute the command
        try:
            cursor = self.connection.cursor()
        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            print("Error : Unable to create the cursor to execute the statement.\n"+str(e))
            return False
        else:
            try:
                cursor.execute(sql_cmd)
            except Exception as e:
                current_function_name = sys._getframe().f_code.co_name
                exc_type, exc_obj, exc_tb = sys.exc_info()
                error_line = exc_tb.tb_lineno
                error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
                print("Error : Unable to execute the SQL Command.\n{}".format(e))
                cursor.close()
                del cursor
                return False
            else:
                cursor.close()
                return cursor

    def commit(self):
        if not self.connection:
            print("Error : Not Connected. Please connect first using connect().")
            return False

        try:
            self.connection.commit()
        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            print("Error : Unable to commit.\n{}".format(e))
            return False
        else:
            return True

    def pd_select(self, table, cols=None, distinct_rows=False, filters=None, limit=None, offset=None):
        if not cols:
            cols = ['*']

        if not filters:
            filters = {}

        if not self.connection:
            print("Error : Not Connected. Please connect first using connect().")
            return False

        if distinct_rows:
            distinct = 'DISTINCT'
        else:
            distinct = ''

        columns = ','.join(map(str, cols))
        where_str = ''
        if filters:
            where_str = " and ".join(["{} like '{}'".format(col, val) for col, val in filters.iteritems()])

            if where_str:
                where_str = "where {}".format(where_str)

        limit_str = ''
        if limit:
            try:
                limit_str = "limit {}".format(limit)
            except:
                limit_str = ''
    
        offset_str = ''
        if offset:
            try:
                offset_str = "offset {}".format(offset)
            except:
                offset_str = ''

   
        try:
            select_query = "SELECT {} {} from {} {} {} {};".format(distinct, columns, table, where_str, limit_str, offset_str)
        
            data = pd.read_sql(select_query, self.connection)
        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            print("Unable to get the Table({}) data in panda data frame.\n{}".format(table, e))
            return False
        else:
            return data


    def get_table_data(self, table_name):
        data = self.pd_select(table=table_name)
        return data

    def insert(self, table, column_names_n_values=None, update_on_duplicate=False, duplicate_check_filter_cols=None):
        """
        This function is used for inserting the data into the given table.
        :param table: This is the name of the table in which to insert the data.
        :param column_names_n_values: This is the dictionary containing the column names and keys and values as the
                                        corresponding column values to be inserted or updated.
        :param update_on_duplicate: If this flag is set to True then it will check if it is inserting the duplicate
                                    data. If so it will perform update statement instead of insert statement.
        :return: True for Successful action eLse False.
        """
        if not column_names_n_values:
            column_names_n_values = {}
        if not duplicate_check_filter_cols:
            duplicate_check_filter_cols = []

        try:
            if not self.connection:
                raise RuntimeError("Please Connect to Database First.")

            if not column_names_n_values:
                error = "Argument '{}' cannot be empty.".format(column_names_n_values)
                raise ValueError(error)


            if update_on_duplicate:
                duplicate_check_filters = {col: val for col, val in column_names_n_values.iteritems() if col in duplicate_check_filter_cols}

                # Check for duplicate entries.
                data = self.pd_select(table=table, filters=duplicate_check_filters)
                if not data.empty:
                    if not self.update(table=table, column_names_n_values=column_names_n_values, filters=duplicate_check_filters):
                        error_msg = "Unable to Update table '{}'".format(table)
                        raise RuntimeError(error_msg)
                else:
                    if not self.insert(table=table, column_names_n_values=column_names_n_values):
                        return False
            else:
                # Create command columns and values strings
                columns_str = ", ".join(["{}".format(col) for col, val in column_names_n_values.iteritems()])
                values_str = ", ".join(["'{}'".format(val) for col, val in column_names_n_values.iteritems()])
                #print(columns_str, values_str, sep='<==>')
                if not columns_str or not values_str:
                    raise ValueError("Columns and their corresponding values both are required for insert.")

                # Create the insert statement
                insert_cmd = "insert into {0} ({1}) values ({2});".format(table, columns_str, values_str)
                #print('====>'+insert_cmd+'\n')

                # Execute the command
                if not self.execute(insert_cmd):
                    error_msg = "Unable to execute the command : '{}'".format(insert_cmd)
                    raise RuntimeError(error_msg)
        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            return None
        else:
            return True

    def delete(self, table, filters=None, reverse_filters=None):
        if not filters:
            filters = {}
        if not reverse_filters:
            reverse_filters = {}

        try:
            if not self.connection:
                raise RuntimeError("Please Connect to Database First.")

            where_cols_n_vals_str = " and ".join(["{} like '{}'".format(col, val) for col, val in filters.iteritems()])

            where_rev_cols_n_vals_str = " and ".join(["{} <> '{}'".format(col, val) for col, val in reverse_filters.iteritems()])

            where_cols_n_vals_str += where_rev_cols_n_vals_str
            if where_cols_n_vals_str:
                where_cols_n_vals_str = "where {}".format(where_cols_n_vals_str)


            # Create the delete statement
            delete_cmd = "delete from {} {};".format(table, where_cols_n_vals_str)

            if not self.execute(delete_cmd):
                error_msg = "Unable to execute the command : '{}'".format(delete_cmd)
                raise RuntimeError(error_msg)

        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            return None
        else:
            return True

    def update(self, table, column_names_n_values=None, filters=None):
        """
        This function is used for inserting the data into the given table.
        :param table: This is the name of the table in which to insert the data.
        :param column_names_n_values: This is the dictionary containing the column names and keys and values as the
                                        corresponding column values to be inserted or updated.
        :param update_on_duplicate: If this flag is set to True then it will check if it is inserting the duplicate
                                    data. If so it will perform update statement instead of insert statement.
        :return: True for Successful action eLse False.
        """
        if not column_names_n_values:
            column_names_n_values = {}
        if not filters:
            filters = {}

        try:
            if not self.connection:
                raise RuntimeError("Please Connect to Database First.")

            if not column_names_n_values:
                error = "Argument '{}' cannot be empty.".format(column_names_n_values)
                raise ValueError(error)

            set_cols_n_vals_str = ", ".join(["{} = '{}'".format(col, val) for col, val in column_names_n_values.iteritems()])

            where_cols_n_vals_str = " and ".join(["{} like '{}'".format(col, val) for col, val in filters.iteritems()])

            if where_cols_n_vals_str:
                where_cols_n_vals_str = "where {}".format(where_cols_n_vals_str)

            # Create the insert statement
            update_cmd = "update {} set {} {};".format(table, set_cols_n_vals_str, where_cols_n_vals_str)

            if not self.execute(update_cmd):
                error_msg = "Unable to execute the command : '{}'".format(update_cmd)
                raise RuntimeError(error_msg)

        except Exception as e:
            current_function_name = sys._getframe().f_code.co_name
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_line = exc_tb.tb_lineno
            error_filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error(In function '{0}' at Line {1} in file {2} ): {3}".format(current_function_name, error_line, error_filename, e))
            return None
        else:
            return True

    def __str__(self):
        return "Database Details :\n\tServer : {0.server}.\n\tType : {0.db_type}.\n\tDatabase : {0.database}.\n\tUser : {0.user}.".format(self)

    def __repr__(self):
        return "Database('{0.server}', '{0.db_type}', '{0.database}', '{0.user}', '*****')".format(self)
