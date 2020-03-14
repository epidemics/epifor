### HEAVILY WIP

class Data:

    def __init__(self, time=datetime.datetime.now()):
        self.time = time
        self.csse = self.load_csse()
        self.ft = self.load_ft()

#        self.cities = self.load_gv_cities()

    def load_csse(self):
        dfs = []
        for f, name in [(CSSE_CONF, "Confirmed"), (CSSE_DEAD, "Deaths"), (CSSE_REC, "Recovered")]:
            df = pd.read_csv(f, header=0)
            dcs = list(df.columns)[4:]
            df[name] = df[dcs].max(axis=1)
            for c in dcs:
                del df[c]
            dfs.append(df)
        d = dfs.pop()
        for d2 in dfs:
            del d2['Lat']
            del d2['Long']
            d = d.merge(d2, on=["Province/State", "Country/Region"], how='outer')
        d['Infections'] = d['Confirmed'] - d['Deaths'] - d['Recovered']
        return d


