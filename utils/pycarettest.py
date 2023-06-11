import psycopg2
conn = psycopg2.connect("localhost")
conn = psycopg2.connect("dbname=postgres user=postgres password=postgres")


import pandas as pd
from pycaret.regression import *


# Open a cursor to perform database operations
plpy = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
def query(sql):
    return plpy.execute(sql).fetchall()

def is_training_require():
    sql = f"select *,(now()::date - last_run::date) AS delta_days, from radhatamapp_datasciencetraining where model_name = '{model_name}'"
    res = query(sql)
    if len(res) == 0 or res[0]['delta_days'] > refresh_model_in_days:
        return True
    
def train_models():    
    ### load sample dataset from pycaret dataset module
    dat = query(data_sql)
    plpy.notice(type(data[0:]))
    data = pd.DataFrame(data[0:])
    # import pycaret regression and init setup
    
    s = setup(data, target = target_column_name, session_id = 123)


    # import RegressionExperiment and init the class
    from pycaret.regression import RegressionExperiment
    exp = RegressionExperiment()

    best = exp.compare_models()	
    save_model(best, model_name)

    # load model
    loaded_from_disk = load_model('my_first_model')

    # save experiment
    save_experiment('my_experiment')


$$ LANGUAGE plpython3u immutable;