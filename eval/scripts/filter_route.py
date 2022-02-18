import json
import pandas as pd
import subprocess

all_routes = set()
with open('route.json') as fh:
    data = json.load(fh)
for node in data:
    all_routes = all_routes | set(data[node])

routes = []
for r in all_routes:
    routes.append({'route':r})
df = pd.DataFrame(routes)
df.to_csv('routes.csv', index=False)

for r in all_routes:
    subprocess.call(['mv', 'user_trajectories/' + r + '.csv', 'edge_routes/'])

