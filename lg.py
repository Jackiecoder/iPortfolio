# Test ML model
# Use logistic regression
# Data seletion: first 50 row

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression


class logistic_regression(object):
    def __init__(self, TICKER, start, end, parameters=('BIDLO', 'ASKHI', 'VOL', 'mktrf', 'smb', 'hml', 'rf')):
        self.sp500 = pd.read_csv('../sp500_day.csv')
        self.TICKER = TICKER
        self.start = start
        self.end = end
        self.para = parameters

    def choice(self):
        sp500_filter = self.sp500[self.sp500['TICKER'] == self.TICKER]
        sp500_filter = sp500_filter.loc[(
            sp500_filter['date'] >= self.start) & (sp500_filter['date'] <= self.end)]
        return sp500_filter

    def input_data(self):
        sp500_filter = self.choice()
        temp = list(sp500_filter['PRC']-sp500_filter['OPENPRC'])
        y = []
        for i in temp:
            if i < 0:
                y.append(0)
            else:
                y.append(1)
        ls = []
        for para in self.para:
            ls.append(sp500_filter[para])
        X = np.array(ls)
        X = np.transpose(X)
        return X, y

    def score_model(self):
        X, y = self.input_data()
        skf = StratifiedKFold(n_splits=5)
        score = 0
        lg = LogisticRegression()
        for train_index, test_index in skf.split(X, y):
            model = lg.fit(X[train_index], [y[i] for i in train_index])
            temp_score = model.score(X[test_index], [y[i]
                                                     for i in test_index])
            score += temp_score
        return score/5

    def predict(self):
        X, y = self.input_data()
        lg = LogisticRegression()
        model = lg.fit(X[:-1], y[:-1])
        predict = model.predict(X[-1].reshape(1, -1))
        return predict


# a = logistic_regression('MSFT', '2000-01-01', '2010-12-31')
# accuracy = a.score_model()
# predict = a.predict()
# print(accuracy, predict)
