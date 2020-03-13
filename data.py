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
}

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
    ['United Kingdom', 'United Kingdon'],
    ['London (UK)', 'London'],
    ['Wuhan', 'Hubei'],
    ['Western Asia', 'Middle East'],
    ['United States of America', 'United states', 'us'],
)

DROP = ['holy see', 'liechtenstein', 'andorra', 'san marino', 'north macedonia',
    'from diamond princess', 'cruise ship', 'saint barthelemy', 'gibraltar', 'faroe islands',
    'channel islands', 'st martin']

EU_STATES = ['Germany', 'Czechia'] ## TODO

MD_CITIES = Path("data/md_cities.tsv")

CITY_SIZES = Path("data/population-city/data/unsd-citypopulation-year-both.csv")

AIRPORTDB = Path("data/GlobalAirportDatabase.txt")

AIRPORTS = Path("data/airports.dat")

FORETOLD = Path("data/foretold_data.json")

CSSE_DIR = Path("data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series")
CSSE_CONF = CSSE_DIR / "time_series_19-covid-Confirmed.csv"
CSSE_REC = CSSE_DIR / "time_series_19-covid-Recovered.csv"
CSSE_DEAD = CSSE_DIR / "time_series_19-covid-Deaths.csv"


