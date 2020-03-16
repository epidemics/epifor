import pathlib
import xml.etree.ElementTree as ET
import logging
import datetime

log = logging.getLogger("fttogv.gleamdef")


class GleamDef:
    def __init__(self, path, base_name=None):
        ET.register_namespace('', 'http://www.gleamviz.org/xmlns/gleamviz_v4_0')
        self.ns = {'gv': 'http://www.gleamviz.org/xmlns/gleamviz_v4_0'}
        self.path = pathlib.Path(path)
        self.tree = ET.parse(self.path)
        self.root = self.tree.getroot()
        self.base_name = base_name or self.path.stem
        self.updated = datetime.datetime.now()
        self.updated_fmt = self.updated.strftime("%Y-%m-%d_%H:%M:%S")
        self._exceptions = self.f1('gv:definition/gv:exceptions')
        self._mitigation_ex = self.f1('gv:definition/gv:exceptions/gv:exception[@continents="1 2 4 3 5"]')
        self._mitigation_val = self._mitigation_ex.find('gv:variable[@name="beta"]', namespaces=self.ns)
        assert self._mitigation_val is not None

    def full_name(self):
        return "{} {} {}".format(self.base_name, self.updated_fmt, self.fmt_params())

    def fa(self, query):
        return self.root.findall(query, namespaces=self.ns)

    def f1(self, query):
        x = self.root.findall(query, namespaces=self.ns)
        if not len(x) == 1:
            raise Exception("Expected one XML object at query {!r}, found {!r}".format(query, x))
        return x[0]

    def save(self, newpath=None):
        if not newpath:
            newpath = self.path.parent / (self.full_name().replace(' ', '_') + ".xml")
        self.f1('./gv:definition').attrib['name'] = self.full_name()
        self.tree.write(newpath)
        log.info("Written GleamViz XML to {!r} (updated from {!r})".format(newpath, self.path))

    def clear_seeds(self):        
        self.f1('./gv:definition/gv:seeds').clear()

    def add_seeds(self, regions, est_key='est_active', compartments={"Infectious": 1.0}, top=None):
        regs = []

        def rec(reg):
            e = reg.est.get(est_key)
            if reg.kind == 'city' and e is not None and e > 1:
                e = max(int(min(e, reg.pop - 1)), 1)
                regs.append((e, reg))
            for r in reg.sub:
                rec(r)
    
        rec(regions.root())
        regs.sort(key=lambda er: er[0], reverse=True)
        sroot = self.f1('./gv:definition/gv:seeds')
        for e, reg in regs[:top]:
            for com_n, com_f in compartments.items():
                if com_f and e * com_f >= 1.0:
                    ET.SubElement(sroot, 'gv:seed', {'number': str(int(e * com_f)), "compartment": com_n, "city": str(reg.gv_id)})

        log.info("Added {} seeds for compartments {!r}".format(len(regs[:top]), list(compartments)))

    @property
    def param_seasonality(self):
        return float(self.f1('./gv:definition/gv:parameters').attrib['seasonalityAlphaMin'])

    @param_seasonality.setter
    def param_seasonality(self, val):
        assert val <= 2.0
        self.f1('./gv:definition/gv:parameters').attrib['seasonalityAlphaMin'] = "{:.3f}".format(val)

    @property
    def param_air_traffic(self):
        return float(self.f1('./gv:definition/gv:parameters').attrib['occupancyRate']) / 100

    @param_air_traffic.setter
    def param_air_traffic(self, val):
        assert val < 1.1
        v = int(max(min(val * 100, 100), 0))
        self.f1('./gv:definition/gv:parameters').attrib['occupancyRate'] = str(v)

    @property
    def params_mitigaton(self):
        return float(self._mitigation_val.get('value'))

    @params_mitigaton.setter
    def params_mitigaton(self, val):
        assert val <= 2.0
        self._mitigation_val.set('value', "{:.3f}".format(val))
        if val == 0.0:
            if self._mitigation_ex in self._exceptions:
                self._exceptions.remove(self._mitigation_ex)
        else:
            if self._mitigation_ex not in self._exceptions:
                self._exceptions.append(self._mitigation_ex)

    def fmt_params(self):
        return "seasonality={:.3f} airtraffic={:.3f} mitigation={:.3f}".format(self.param_seasonality, self.param_air_traffic, self.params_mitigaton)
