import copy
import datetime
import logging
import pathlib
import xml.etree.ElementTree as ET

import dateutil

log = logging.getLogger("fttogv.gleamdef")


class GleamDef:
    def __init__(self, path):
        ET.register_namespace('', 'http://www.gleamviz.org/xmlns/gleamviz_v4_0')        
        self.ns = {'gv': 'http://www.gleamviz.org/xmlns/gleamviz_v4_0'}
        self.path = pathlib.Path(path).resolve()
        self.tree = ET.parse(self.path)
        self.root = self.tree.getroot()

        self.updated = datetime.datetime.now()
        self.updated_fmt = self.updated.strftime("%Y-%m-%d_%H:%M:%S")

    def copy(self):
        return copy.deepcopy(self)

    def fa(self, query):
        return self.root.findall(query, namespaces=self.ns)

    def f1(self, query):
        x = self.root.findall(query, namespaces=self.ns)
        if not len(x) == 1:
            raise Exception("Expected one XML object at query {!r}, found {!r}".format(query, x))
        return x[0]

    def save(self, filename=None, *, prefix=None):
        if filename is None:
            assert prefix is not None
            prefix = pathlib.Path(prefix)
            filename = prefix.parent / (self.full_name(prefix.stem).replace(' ', '_') + ".xml")
            self.name = self.full_name(prefix.stem)
        else:
            filename = pathlib.Path(filename)
            self.name = self.full_name(filename.stem)
        self.tree.write(filename) #, default_namespace=self.ns['gv'])
        log.info("Written Gleam definition XML to {!r} (updated from {!r})".format(filename, self.path))

    def clear_seeds(self):        
        self.f1('./gv:definition/gv:seeds').clear()

    def add_seeds(self, regions, est_key='est_active', compartments=None, top=None):
        if compartments is None:
            compartments = {"Infectious": 1.0}
        regs = []

        def rec(reg):
            e = reg.est.get(est_key)
            if reg.kind == 'city' and e is not None and e > 1:
                e = max(int(min(e, reg.pop - 1)), 1)
                regs.append((e, reg))
            for r in reg.sub:
                rec(r)
    
        rec(regions.root)
        regs.sort(key=lambda er: er[0], reverse=True)
        sroot = self.f1('./gv:definition/gv:seeds')
        for e, reg in regs[:top]:
            for com_n, com_f in compartments.items():
                if com_f and e * com_f >= 1.0:
                    ET.SubElement(sroot, 'seed', {'number': str(int(e * com_f)), "compartment": com_n, "city": str(reg.gleam_id)})

        log.info("Added {} seeds for compartments {!r}".format(len(regs[:top]), list(compartments)))

    @property
    def name(self):
        return self.f1('./gv:definition').attrib['name']

    @name.setter
    def name(self, val):
        self.f1('./gv:definition').attrib['name'] = val

    @property
    def param_seasonality(self):
        return float(self.f1('./gv:definition/gv:parameters').attrib['seasonalityAlphaMin'])

    @param_seasonality.setter
    def param_seasonality(self, val):
        assert val <= 2.0
        self.f1('./gv:definition/gv:parameters').attrib['seasonalityAlphaMin'] = "{:.2f}".format(val)

    @property
    def param_air_traffic(self):
        return float(self.f1('./gv:definition/gv:parameters').attrib['occupancyRate']) / 100

    @param_air_traffic.setter
    def param_air_traffic(self, val):
        assert val < 1.1
        v = int(max(min(val * 100, 100), 0))
        self.f1('./gv:definition/gv:parameters').attrib['occupancyRate'] = str(v)

    def _mitigation_nodes(self):
        return self.fa('gv:definition/gv:exceptions/gv:exception[@continents="1 2 4 3 5"]/gv:variable[@name="beta"]')

    @property
    def param_mitigation(self):
        mns = self._mitigation_nodes()
        if len(mns) == 0:
            return 0.0
        if len(mns) > 1:
            raise Exception("Multiple global mitigation nodes: {}!".format(mns))
        return float(mns[0].get('value'))

    @param_mitigation.setter
    def param_mitigation(self, val):
        assert val <= 2.0
        mns = self._mitigation_nodes()
        if len(mns) > 1:
            raise Exception("Multiple global mitigation nodes: {}!".format(mns))
        if val == 0.0:
            if len(mns) > 0:
                pt = self.f1('gv:definition/gv:exceptions/gv:exception[@continents="1 2 4 3 5"]')
                self.f1('gv:definition/gv:exceptions').remove(pt)
        else:
            if len(mns) == 0:
                raise Exception("Can't set mitigation >0 in file withou global mitigation Exception node.")
            mns[0].set('value', "{:.2f}".format(val))

    def get_id(self):
        return self.f1('gv:definition').get('id')

    def set_id(self, val):
        return self.f1('gv:definition').set('id', str(val))

    def fmt_params(self):
        return "seasonality={:.2f} airtraffic={:.2f} mitigation={:.2f}".format(self.param_seasonality, self.param_air_traffic, self.param_mitigation)

    def full_name(self, base_name):
        return "{} {} {}".format(base_name, self.updated_fmt, self.fmt_params())

    def get_start_date(self):
        return dateutil.parser.parse(self.f1('./gv:definition/gv:parameters').get('startDate'))
