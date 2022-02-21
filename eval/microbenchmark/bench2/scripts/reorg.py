import pandas as pd
import os

newd = "users/10nodes/1kusers/set1/nonoverlapped2"
oldd = "users/10nodes/1kusers/set1/nonoverlapped"
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
        ndf.to_csv(nf, index=False)
    except Exception as e:
        print(e)
        print('{} to {} failed'.format(ff, nf))
