# -*- coding: utf-8 -*-
"""
Created on Sun Feb  9 06:45:56 2020

@author: 40915
"""


import numpy as np
import pandas as pd
#from matplotlib import cm, pyplot as plt
from hmmlearn.hmm import GaussianHMM
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn import preprocessing

#df = pd.read_csv('data.csv')
# df1=df.loc[df['TICKER']=='AMZN']
# df1['date']=pd.to_datetime(df1['date'],format='%Y%m%d')
# df1=df1.loc[(df1['date']>='20100101')&(df1['date']<='20151231')]
# predict_close=[]
# print(type(predict_close))
#datenumber= df1.loc[df1['date']<'20100101']
# df1=df1.loc[(df1['date']>='20100101')&(df1['date']<='20101231')]
# totaldays=len(df1)
# print(len(datenumber))
# print(type(len(datenumber)))
# print(type(totaldays))
# close_test=list(df1['OPENPRC'])
# close_test=close_test[len(datenumber)+totaldays-10:len(datenumber)+totaldays]


def hmmpredict(ticker, startdate, enddate):
    df = pd.read_csv('../data.csv')
    # startdate = ''.join([startdate[i]
    #                      for i in range(len(startdate)) if startdate[i] != '-'])
    # enddate = ''.join([enddate[i]
    #                    for i in range(len(enddate)) if enddate[i] != '-'])
    # print(startdate, enddate)
    df1 = df.loc[df['TICKER'] == ticker]
    # print(df1['date'][0])
    df1['date'] = pd.to_datetime(df1['date'], format='%Y%m%d')

    # df2=df1.loc[df1['date']<startdate]
    #datenumber = len(df2)

    df1 = df1.loc[(df1['date'] >= startdate) & (df1['date'] <= enddate)]
    # totaldays=len(df1)
    # dateinterval=totaldays//5
#    print(datenumber+totaldays-10)
#    print(datenumber+totaldays)
#    close_test=list(df1['OPENPRC'])
#    print(len(close_test))
#    close_test=close_test[-10:]
#    print(len(close_test))
    # print(type(dateinterval))

    volume = df1['VOL']
    close = df1['PRC']
    volume_test = list(df1['VOL'])

    open_test = list(df1['OPENPRC'])
    close_test = list(df1['PRC'])
    #high_test= df1['ASKHI']
    #low_test = df1['BIDLO']

    logDel = np.log(np.array(df1['ASKHI'])) - np.log(np.array(df1['BIDLO']))
    from scipy import stats
    from sklearn.preprocessing import StandardScaler
    from sklearn import preprocessing

    logDel_stand, _ = stats.boxcox(logDel)
    rescaled_boxcox_logDel = preprocessing.scale(
        logDel_stand, axis=0, with_mean=True, with_std=True, copy=False)

    logRet_1 = np.array(np.diff(np.log(close)))
    logRet_5 = np.log(np.array(close[5:])) - np.log(np.array(close[:-5]))
    rescaled_logRet_5 = preprocessing.scale(
        logRet_5, axis=0, with_mean=True, with_std=True, copy=False)
    logVol_5 = np.log(np.array(volume[5:])) - np.log(np.array(volume[:-5]))
    rescaled_logVol_5 = preprocessing.scale(
        logVol_5, axis=0, with_mean=True, with_std=True, copy=False)

    rescaled_boxcox_logDel = rescaled_boxcox_logDel[5:]
    logRet_1 = logRet_1[4:]
    close = close[5:]
    #Date = pd.to_datetime(df.index[5:])

    rescaled_A = np.column_stack(
        [rescaled_boxcox_logDel, rescaled_logRet_5, rescaled_logVol_5])

    model = GaussianHMM(n_components=3, covariance_type="full",
                        n_iter=2000).fit(rescaled_A)
    hidden_states = model.predict(rescaled_A)

    frac = np.linspace(-0.1, 0.1, 20)+1
    possible_close = np.multiply(frac, np.transpose([open_test]))
    space = np.linspace(0, 0.1, 10)
    n_logHighLow = []
    for i in range(10):
        for j in range(10):
            n_logHighLow.append([np.log(1+space[i])-np.log(1-space[j])])
# len(n_logHighLow)
    space_close = np.linspace(-0.1, 0.1, 20)
    n_logClose = []
    for i in range(20):
        for j in range(20):
            n_logClose.append(
                [np.log(1+space_close[i])-np.log(1+space_close[j])])
# len(n_logClose)
    import itertools
    frac_possible = np.array(
        list(itertools.product(space_close, space, space)))
# len(frac_possible)
    # print(len(possible_close))
    def get_possible_outcomes(n_date):

        n_possible_close = possible_close[n_date, :]
        n_tomorrow_possible_close = possible_close[n_date+1, :]
#        print(len(n_tomorrow_possible_close))
#        print(n_date)
        n_volume = volume_test[n_date]
        n_tomorrow_volume = volume_test[n_date+1]

        n_logDel = np.array(n_logHighLow)
        n_logRet = []
        for i in n_possible_close:
            for j in n_tomorrow_possible_close:
                # print(type(n_logRet))
                n_logRet.append(np.log(j)-np.log(i))
                #n_logRet = np.array(n_logRet)
                n_logVol = np.log(n_tomorrow_volume) - np.log(n_volume)

        possible_outcomes = np.array(list(itertools.product(
            n_logDel, n_logRet, [n_logVol])))
#     print(possible_outcomes[0:9])

        outcome_score = []
        for possible_outcome in possible_outcomes:
            outcome_score.append(model.score(possible_outcome.reshape(-1, 1)))
        most_probable_outcome = possible_outcomes[np.argmax(outcome_score)]

        return most_probable_outcome

    def get_frac(n_date, most_probable_outcome):
        highlow = most_probable_outcome[0]
        close_diff = most_probable_outcome[1]
        close = 0
        for i in range(10):
            for j in range(10):
                if np.log(1+space[i])-np.log(1-space[j]) == highlow:
                    high = (1+space[i]) * open_test[n_date]
                    low = (1-space[j]) * open_test[n_date]

        close = list(df1['PRC'])[n_date-5] * np.exp(close_diff)
        # print(type(close))

        if high != None and low != None and close != None:
            return high, low, close
    # print('fxxk')
    predict_close = []
    diff = []
    days = np.array(range(10))
    # print(days)
    diff_arr = []

    for n_date in range(-10, 0):
        close_test = list(df1['OPENPRC'])
        # print(close_test)
        most_probable_outcome = get_possible_outcomes(n_date)
        # print(0)
        n_high, n_low, n_close = get_frac(n_date, most_probable_outcome)
        # print(n_close)
        predict_close.append(n_close)
        # print(predict_close)

        close_test = close_test[-10:]
        # print(close_test)
    for i in range(10):
        diff.append([(predict_close[i]-np.array(close_test)[i]) /
                     np.array(close_test)[days[i]]])
#        print(predict_close(close[i]))
#        print(np.array(close_test)[i])
#        diff.append([(n_close-np.array(close_test)[n_date])/np.array(close_test)[days[n_date]]])
    diff_arr.append(np.array(diff))
#    print(predict_close)
    # return predict_close

    confidencelvl = np.sum(np.abs(diff_arr))/len(diff_arr)
#    print(confidencelvl)
    # return confidencelvl

    a = {'prediction of next ten days price': predict_close,
         'deviation': confidencelvl}
    return a


test1 = hmmpredict('AMZN', '20120101', '20121231')
print(test1)
