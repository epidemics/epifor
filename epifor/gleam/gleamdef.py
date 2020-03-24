import copy
import datetime
import logging
import pathlib
import xml.etree.ElementTree as ET

import dateutil

log = logging.getLogger(__name__)


class GleamDef:
    def __init__(self, path):
        ET.register_namespace("", "http://www.gleamviz.org/xmlns/gleamviz_v4_0")
        self.ns = {"gv": "http://www.gleamviz.org/xmlns/gleamviz_v4_0"}
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
            raise Exception(
                "Expected one XML object at query {!r}, found {!r}".format(query, x)
            )
        return x[0]

    def save(self, filename=None, *, prefix=None):
        if filename is None:
            assert prefix is not None
            prefix = pathlib.Path(prefix)
            filename = prefix.parent / (
                self.full_name(prefix.stem).replace(" ", "_") + ".xml"
            )
        else:
            filename = pathlib.Path(filename)
        self.tree.write(filename)  # , default_namespace=self.ns['gv'])
        log.info(f"Written Gleam definition to {filename}")

    def clear_seeds(self):
        self.f1("./gv:definition/gv:seeds").clear()

    def add_seeds(self, regions, est_key="est_active", compartments=None, top=None):
        if compartments is None:
            compartments = {"Infectious": 1.0}
        regs = []

        def rec(reg):
            e = reg.est.get(est_key)
            if reg.kind == "city" and e is not None and e > 1:
                e = max(int(min(e, reg.pop - 1)), 1)
                regs.append((e, reg))
            for r in reg.sub:
                rec(r)

        rec(regions.root)
        regs.sort(key=lambda er: er[0], reverse=True)
        sroot = self.f1("./gv:definition/gv:seeds")
        for e, reg in regs[:top]:
            for com_n, com_f in compartments.items():
                if com_f and e * com_f >= 1.0:
                    seed = ET.SubElement(
                        sroot,
                        "seed",
                        {
                            "number": str(int(e * com_f)),
                            "compartment": com_n,
                            "city": str(reg.gleam_id),
                        },
                    )
                    seed.tail = "\n      "

        log.info(
            "Added {} seeds for compartments {!r}".format(
                len(regs[:top]), list(compartments)
            )
        )

    ### General attributes

    def get_name(self):
        return self.f1("./gv:definition").attrib["name"]

    def set_name(self, val):
        self.f1("./gv:definition").attrib["name"] = val

    def get_id(self):
        return self.f1("gv:definition").get("id")

    def set_id(self, val):
        return self.f1("gv:definition").set("id", str(val))

    ### Parameters

    def get_start_date(self):
        return dateutil.parser.parse(
            self.f1("./gv:definition/gv:parameters").get("startDate")
        )

    def set_start_date(self, date):
        if isinstance(date, datetime.datetime):
            date = date.date()
        assert isinstance(date, datetime.date)
        self.f1("./gv:definition/gv:parameters").set("startDate", date.isoformat())

    def get_seasonality(self):
        return float(
            self.f1("./gv:definition/gv:parameters").get("seasonalityAlphaMin")
        )

    def set_seasonality(self, val):
        assert val <= 2.0
        self.f1("./gv:definition/gv:parameters").set(
            "seasonalityAlphaMin", f"{val:.2f}"
        )

    def get_beta(self):
        return float(
            self.f1(
                './gv:definition/gv:compartmentalModel/gv:variables/gv:variable[@name="beta"]'
            ).get("value")
        )

    def set_beta(self, val):
        assert val >= 0.0
        self.f1(
            './gv:definition/gv:compartmentalModel/gv:variables/gv:variable[@name="beta"]'
        ).set("value", f"{val:.2f}")

    def get_traffic_occupancy(self):
        "Note: this an integer in percent"
        return int(self.f1("./gv:definition/gv:parameters").get("occupancyRate"))

    def set_traffic_occupancy(self, val):
        "Note: this must be an integer in percent"
        assert isinstance(val, int)
        assert 0 <= val and val <= 100
        self.f1("./gv:definition/gv:parameters").set("occupancyRate", str(int(val)))

    ### Naming conveniences

    def fmt_params(self):
        return f"seasonality={self.get_seasonality():.2f} traffic={self.get_traffic_occupancy()} beta={self.get_beta():.2f}"

    def full_name(self, base_name):
        return "{} {} {}".format(base_name, self.updated_fmt, self.fmt_params())

    ### Exceptions handling

    def _mitigation_nodes(self):
        return self.fa(
            'gv:definition/gv:exceptions/gv:exception[@continents="1 2 4 3 5"]/gv:variable[@name="beta"]'
        )

    @property
    def param_mitigation(self):
        mns = self._mitigation_nodes()
        if len(mns) == 0:
            return 0.0
        if len(mns) > 1:
            raise Exception("Multiple global mitigation nodes: {}!".format(mns))
        return float(mns[0].get("value"))

    @param_mitigation.setter
    def param_mitigation(self, val):
        assert val <= 2.0
        mns = self._mitigation_nodes()
        if len(mns) > 1:
            raise Exception("Multiple global mitigation nodes: {}!".format(mns))
        if val == 0.0:
            if len(mns) > 0:
                pt = self.f1(
                    'gv:definition/gv:exceptions/gv:exception[@continents="1 2 4 3 5"]'
                )
                self.f1("gv:definition/gv:exceptions").remove(pt)
        else:
            if len(mns) == 0:
                raise Exception(
                    "Can't set mitigation >0 in file withou global mitigation Exception node."
                )
            mns[0].set("value", "{:.2f}".format(val))
