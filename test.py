from fama_french_monthly import famaFrenchMonthly
import sys
import datetime
from lg import logistic_regression
# from hmm_model import hmmpredict

model = sys.argv[1]
company_name = sys.argv[2]
start_data = sys.argv[3]
end_data = sys.argv[4]
if model == "CAMP":
    a = famaFrenchMonthly(company_name, start_data, end_data)
    capm = a.predict_CAPM()
    print(f"excess return = {capm['y_CAPM']}, \npredicted actual return = {capm['ret_pre_CAPM']}, \npredicted price = {capm['prc_pre_CAPM']}, \nexplaination power = {capm['CAPM_rsquared']}")
if model == "FF3":
    a = famaFrenchMonthly(company_name, start_data, end_data)
    ff3 = a.predict_CAPM()
    print(f"excess return = {ff3['y_CAPM']}, \npredicted actual return = {ff3['ret_pre_CAPM']}, \npredicted price = {ff3['prc_pre_CAPM']}, \nexplaination power = {ff3['CAPM_rsquared']}")
if model == "LG":
    a = logistic_regression(company_name, start_data, end_data)
    upOrDown = a.predict()
    accuracy = a.score_model()
    if upOrDown[0]:
        print(
            f"This stock price will increase with {accuracy*100}% confidence!")
    else:
        print(
            f"This stock price will decrease with {accuracy*100}% confidence!")

if model == "HMM":
    a = hmmpredict(company_name, start_data, end_data)
    print(
        f"prediction of next ten days price is {a['prediction of next ten days price']}, and deviation is {a['deviation']}")
