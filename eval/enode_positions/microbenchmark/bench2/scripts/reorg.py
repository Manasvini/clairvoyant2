import pandas as pd
import os

newd = "users_m2_new2"
oldd = "users_m2_new"
os.mkdir(newd)
files = os.listdir(oldd)

for f in files:
    if 'swp' in f:
        continue
    ff = oldd + '/' + f
    nf = newd + '/' + f
    try:
        df = pd.read_csv(ff)
        ndf = df.reindex(columns=['userId','time','x','y','z','velocity'])
        ndf['time'] = 400 + ndf['time']
        ndf.to_csv(nf, index=False)
    except Exception as e:
        print(e)
        print('{} to {} failed'.format(ff, nf))
