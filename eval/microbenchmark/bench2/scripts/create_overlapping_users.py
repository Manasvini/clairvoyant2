import pandas as pd
import os
import random

newd = "users/10nodes/1kusers/set5/overlapped"
oldd = "users/10nodes/1kusers/set5/nonoverlapped"
os.mkdir(newd)

files = os.listdir(oldd)

start = -1
end = -1

for f in sorted(files, key=lambda x : int(x.split('.')[0][4:])):
    if 'swp' in f:
        continue
    ff = oldd + '/' + f
    nf = newd + '/' + f
    try:
        df = pd.read_csv(ff)
        ndf = df.reindex(columns=['userId','time','x','y','z','velocity'])

        if start != -1:
            nstart = int(random.uniform(start, end))
            #print(oldd, df['time'].iloc[0], df['time'].iloc[-1], '{} from ({},{})'.format(nstart, start, end))
            ndf['time'] = df['time'] - df['time'].iloc[0] + nstart

        start = ndf['time'].iloc[0]
        end = ndf['time'].iloc[-1]

        
        ndf.to_csv(nf, index=False)
    except Exception as e:
        print(e)
        print('{} to {} failed'.format(ff, nf))
