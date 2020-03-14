from pathlib import Path

STATES = {
    'United States': [
        ('Alabama', 'AL'),
        ('Alaska', 'AK'),
        ('Arizona', 'AZ'),
        ('Arkansas', 'AR'),
        ('California', 'CA'),
        ('Colorado', 'CO'),
        ('Connecticut', 'CT'),
        ('Delaware', 'DE'),
        ('Florida', 'FL'),
        ('Georgia', 'GA'),
        ('Hawaii', 'HI'),
        ('Idaho', 'ID'),
        ('Illinois', 'IL'),
        ('Indiana', 'IN'),
        ('Iowa', 'IA'),
        ('Kansas', 'KS'),
        ('Kentucky', 'KY'),
        ('Louisiana', 'LA'),
        ('Maine', 'ME'),
        ('Maryland', 'MD'),
        ('Massachusetts', 'MA'),
        ('Michigan', 'MI'),
        ('Minnesota', 'MN'),
        ('Mississippi', 'MS'),
        ('Missouri', 'MO'),
        ('Montana', 'MT'),
        ('Nebraska', 'NE'),
        ('Nevada', 'NV'),
        ('New Hampshire', 'NH'),
        ('New Jersey', 'NJ'),
        ('New Mexico', 'NM'),
        ('New York', 'NY'),
        ('North Carolina', 'NC'),
        ('North Dakota', 'ND'),
        ('Ohio', 'OH'),
        ('Oklahoma', 'OK'),
        ('Oregon', 'OR'),
        ('Pennsylvania', 'PA'),
        ('Rhode Island', 'RI'),
        ('South Carolina', 'SC'),
        ('South Dakota', 'SD'),
        ('Tennessee', 'TN'),
        ('Texas', 'TX'),
        ('Utah', 'UT'),
        ('Vermont', 'VT'),
        ('Virginia', 'VA'),
        ('Washington', 'WA'),
        ('West Virginia', 'WV'),
        ('Wisconsin', 'WI'),
        ('Wyoming', 'WY'),
        (['District of Columbia', 'washington, d.c.'], 'DC'),
    ],
    'Canada': [
        ('Alberta', 'AB'),
        ('British Columbia', 'BC'),
        ('Manitoba', 'MB'),
        ('New Brunswick', 'NB'),
        ('Newfoundland and Labrador', 'NL'),
        ('Northwest Territories', 'NT'),
        ('Nova Scotia', 'NS'),
        ('Nunavut', 'NU'),
        ('Ontario', 'ON'),
        ('Prince Edward Island', 'PE'),
        ('Quebec', 'QC'),
        ('Saskatchewan', 'SK'),
        ('Yukon', 'YT'),
    ],
    'China': [
        ('Anhui', None),('Fujian', None),('Gansu', None),('Guangdong', None),('Guizhou', None),('Hainan', None),('Hebei', None),('Heilongjiang', None),('Henan', None),('Hubei', None),('Hunan', None),('Jiangsu', None),('Jiangxi', None),('Jilin', None),('Liaoning', None),('Qinghai', None),('Shaanxi', None),('Shandong', None),('Shanxi', None),('Sichuan', None),('Yunnan', None),('Zhejiang', None),
        ('Guangxi', None),('Inner Mongolia', None),('Ningxia', None),('Tibet', None),('Xinjiang', None),('Hong Kong', None),(['Macao', 'Macau'], None),('Beijing', None),('Chongqing', None),('Shanghai', None),('Tianjin', None),
    ],
    'Australia': [
        (['australian capital territory', 'Federal Capital Territory'], None), ('New South Wales', None),('Victoria', None),('Queensland', None),('South Australia', None),('Western Australia', None),('Tasmania', None),('Northern Territory', None),
    ],
}

UNABBREV = {}
for _c, _ss in STATES.items():
    for _s, _a in _ss:
        UNABBREV[_a] = _s

ALIASES = (
    ['Egypt, Arab Rep.', 'Egypt'],
    ['Slovak Republic', 'Slovakia'],
    ['Korea, Rep.', 'Korea, South', 'South korea'],
    ['Czech Republic', 'Czechia'],
    ['Taiwan', 'Taiwan*'],
    ['Russian Federation', 'Russia'],
    ['Congo, Dem. Rep.', 'Congo (Kinshasa)'],
    ['Lhasa', 'Tibet'],
    ['St Barthelemy', 'Saint Barthelemy'],
    ['Baltimore', 'Washington'],
    ['United Kingdom', 'United Kingdon', 'UK'],
    ['London (UK)', 'London'],
    ['Wuhan', 'Hubei'],
    ['Western Asia', 'Middle East'],
    ['United States of America', 'United states', 'us'],
    ['korea, dem. rep.', 'korea, north'],
    ['cape verde', 'cabo verde'],
    ['lao pdr', 'laos'],
    ['myanmar', 'burma'],
    ['gambia', 'gambia, the'],
)

DROP = ['holy see', 'liechtenstein', 'andorra', 'san marino', 'north macedonia',
    'from diamond princess', 'cruise ship', 'saint barthelemy', 'gibraltar', 'faroe islands',
    'channel islands', 'st martin', 'diamond princess', 'grand princess']

EU_STATES = ['Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden']

MD_CITIES = Path("data/md_cities.tsv")

CITY_SIZES = Path("data/population-city/data/unsd-citypopulation-year-both.csv")
CITY_SIZES_W = Path("data/worldcities.csv")

AIRPORTDB = Path("data/GlobalAirportDatabase.txt")

AIRPORTS = Path("data/airports.dat")

FORETOLD = Path("data/foretold_data.json")

CSSE_DIR = Path("data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series")
CSSE_CONF = CSSE_DIR / "time_series_19-covid-Confirmed.csv"
CSSE_REC = CSSE_DIR / "time_series_19-covid-Recovered.csv"
CSSE_DEAD = CSSE_DIR / "time_series_19-covid-Deaths.csv"



