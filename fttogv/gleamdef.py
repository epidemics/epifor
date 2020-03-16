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

    def full_name(self):
        return "{} {} {}".format(self.base_name, self.updated_fmt, self.fmt_params())

    def get(self, path):
        rs = self.root.findall(path, namespaces=self.ns)
        if not len(rs) == 1:
            raise Exception("Expected one XML object at path {!r}, found {!r}".format(path, rs))
        return rs[0]

    def save(self, newpath=None):
        if not newpath:
            newpath = self.path.parent / (self.full_name().replace(' ', '_') + ".xml")
        self.get('./gv:definition').attrib['name'] = self.full_name()
        self.tree.write(newpath)
        log.info("Written GleamViz XML to {!r} (updated from {!r})".format(newpath, self.path))

    def clear_seeds(self):        
        self.get('./gv:definition/gv:seeds').clear()

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
        sroot = self.get('./gv:definition/gv:seeds')
        for e, reg in regs[:top]:
            for com_n, com_f in compartments.items():
                if com_f and e * com_f >= 1.0:
                    ET.SubElement(sroot, 'seed', {'number': str(int(e * com_f)), "compartment": com_n, "city": str(reg.gv_id)})

        log.info("Added {} seeds for compartments {!r}".format(len(regs[:top]), list(compartments)))

    @property
    def param_seasonality(self):
        return float(self.get('./gv:definition/gv:parameters').attrib['seasonalityAlphaMin'])

    @param_seasonality.setter
    def param_seasonality(self, val):
        assert val <= 2.0
        self.get('./gv:definition/gv:parameters').attrib['seasonalityAlphaMin'] = "{:.3f}".format(val)

    @property
    def param_air_traffic(self):
        return float(self.get('./gv:definition/gv:parameters').attrib['occupancyRate']) / 100

    @param_air_traffic.setter
    def param_air_traffic(self, val):
        assert val <= 2.0
        self.get('./gv:definition/gv:parameters').attrib['occupancyRate'] = "{:.3f}".format(val * 100)

    def get_mitigation_variable_node(self):
        exs = self.root.findall('./gv:definition/gv:exceptions/gv:exception', namespaces=self.ns)
        assert len(exs) >= 1
        for e in exs:
            if e.attrib['continents'] == "1 2 4 3 5":
                for v in e.findall('./gv:variable', namespaces=self.ns):
                    if v.attrib['name'] == 'beta':
                        return v
        raise Exception("Global mitigation Exception node (with continents='1 2 4 3 5') not found")

    @property
    def params_mitigaton(self):
        return float(self.get_mitigation_variable_node().attrib['value'])

    @params_mitigaton.setter
    def params_mitigaton(self, val):
        assert val <= 2.0
        self.get_mitigation_variable_node().attrib['value'] = "{:.3f}".format(val)

    def fmt_params(self):
        return "seasonality={:.3f} airtraffic={:.3f} mitigation={:.3f}".format(self.param_seasonality, self.param_air_traffic, self.params_mitigaton)