### load sample dataset from pycaret dataset module
from pycaret.datasets import get_data
data = get_data('insurance')
print(data.info())
# import pycaret regression and init setup
from pycaret.regression import *
# import RegressionExperiment and init the class
from pycaret.regression import RegressionExperiment
exp = RegressionExperiment()

# init setup on exp
exp.setup(data, target = 'charges', session_id = 123)

# compare baseline models
best = exp.compare_models()
 	
save_model(best, 'my_first_model')

# load model
loaded_from_disk = load_model('my_first_model')

# copy data and drop charges
new_data = data.copy()
# new_data.drop('charges', axis=1, inplace=True)
new_data.head()
# predict model on new_data
predictions = predict_model(loaded_from_disk, data = new_data)
print(predictions.head())