import statsmodels.formula.api as sm
from statsmodels.iolib.summary2 import summary_col
import numpy as np
import pandas as pd


class famaFrenchMonthly(object):
    def __init__(self, TICKER, start, end):
        self.sp500 = pd.read_csv('../sp500_mon.csv')
        self.TICKER = TICKER
        self.start = start
        self.end = end

    def choice(self):
        sp500_filter = self.sp500[self.sp500['TICKER'] == self.TICKER]
        # sp500_filter['date'] = pd.to_datetime(
        #     sp500_filter['date'], format='%Y%m%d')
        sp500_filter = sp500_filter.loc[(
            sp500_filter['date'] >= self.start) & (sp500_filter['date'] <= self.end)]
        # print(sp500_filter.head())
        return sp500_filter


# train model

    def regression(self):
        d1 = self.choice()
        CAPM = sm.ols(formula='exret ~ mktrf', data=d1).fit(
            cov_type='HAC', cov_kwds={'maxlags': 1})
        FF3 = sm.ols(formula='exret ~ mktrf + smb +hml',
                     data=d1).fit(cov_type='HAC', cov_kwds={'maxlags': 1})

        CAPMcoeff = CAPM.params
        FF3coeff = FF3.params

        CAPMtstat = CAPM.tvalues
        FF3tstat = FF3.tvalues

        CAPMrsquared = CAPM.rsquared
        FF3rsquared = FF3.rsquared

        res = pd.DataFrame({'CAPMcoeff': CAPMcoeff, 'CAPMtstat': CAPMtstat, 'CAPMrsquared': CAPMrsquared,  'FF3coeff': FF3coeff, 'FF3tstat': FF3tstat, 'FF3rsquared': FF3rsquared},
                           index=['Intercept', 'mktrf', 'smb', 'hml'])
        return res

# do predict
    def predict_CAPM(self):
        d1 = self.choice()
        res = self.regression()
        last_month = d1.loc[d1['date'] == self.end]

        y_CAPM = float(res.iat[0, 0] + res.iat[1, 0] * last_month['mktrf'])
        ret_pre_CAPM = float(y_CAPM + last_month['rf'])
        prc_pre_CAPM = float((1+ret_pre_CAPM)*last_month['PRC'])
        # print({'y_CAPM': y_CAPM, 'ret_pre_CAPM': ret_pre_CAPM,
        #        'prc_pre_CAPM': prc_pre_CAPM, 'CAPM_rsquared': float(res.iat[0, 2])})
        return {'y_CAPM': y_CAPM, 'ret_pre_CAPM': ret_pre_CAPM, 'prc_pre_CAPM': prc_pre_CAPM, 'CAPM_rsquared': float(res.iat[0, 2])}

    def predict_FF3(self):
        d1 = self.choice()
        res = self.regression()
        last_month = d1.loc[d1['date'] == self.end]

        y_FF3 = float(res.iat[0, 3] + res.iat[1, 3] * last_month['mktrf'] +
                      res.iat[2, 3] * last_month['smb']+res.iat[1, 3] * last_month['hml'])
        ret_pre_FF3 = float(y_FF3 + last_month['rf'])
        prc_pre_FF3 = float((1+ret_pre_FF3)*last_month['PRC'])

        # print({'y_FF3': y_FF3, 'ret_pre_FF3': ret_pre_FF3,
        #        'prc_pre_FF3': prc_pre_FF3, 'FF3_rsquared': float(res.iat[0, 5])})
        return {'y_FF3': y_FF3, 'ret_pre_FF3': ret_pre_FF3, 'prc_pre_FF3': prc_pre_FF3, 'FF3_rsquared': float(res.iat[0, 5])}


# a = famaFrenchMonthly('MSFT', '2000-01-01', '2010-12-31')
# capm = a.predict_CAPM()
# ff3 = a.predict_FF3()
# print(capm, ff3)

# predict_CAPM('MSFT', '20000101', '20101231')
# predict_FF3('MSFT', '20000101', '20101231')
