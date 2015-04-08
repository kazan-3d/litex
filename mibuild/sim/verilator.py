# This file is Copyright (c) 2015 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import os, subprocess

from migen.fhdl.std import *
from migen.fhdl.structure import _Fragment
from mibuild.generic_platform import *

from mibuild import tools
from mibuild.sim import common

def _build_tb(platform, vns, serial, template):

	def io_name(ressource, subsignal=None):
		res = platform.lookup_request(ressource)
		if subsignal is not None:
			res = getattr(res, subsignal)
		return vns.get_name(res)

	ios = """
#define SYS_CLK dut->{sys_clk}
""".format(sys_clk=io_name("sys_clk"))

	if serial == "pty":
		ios += "#define WITH_SERIAL_PTY"
	elif serial == "console":
		pass
	else:
		raise ValueError
	try:
		ios += """
#define SERIAL_SOURCE_STB dut->{serial_source_stb}
#define SERIAL_SOURCE_ACK dut->{serial_source_ack}
#define SERIAL_SOURCE_DATA   dut->{serial_source_data}

#define SERIAL_SINK_STB dut->{serial_sink_stb}
#define SERIAL_SINK_ACK dut->{serial_sink_ack}
#define SERIAL_SINK_DATA   dut->{serial_sink_data}
""".format(
	serial_source_stb=io_name("serial", "source_stb"),
	serial_source_ack=io_name("serial", "source_ack"),
	serial_source_data=io_name("serial", "source_data"),

	serial_sink_stb=io_name("serial", "sink_stb"),
	serial_sink_ack=io_name("serial", "sink_ack"),
	serial_sink_data=io_name("serial", "sink_data"),
	)
	except:
		pass

	try:
		ios += """
#define ETH_SOURCE_STB		dut->{eth_source_stb}
#define ETH_SOURCE_ACK		dut->{eth_source_ack}
#define ETH_SOURCE_DATA		dut->{eth_source_data}

#define ETH_SINK_STB		dut->{eth_sink_stb}
#define ETH_SINK_ACK		dut->{eth_sink_ack}
#define ETH_SINK_DATA	dut->{eth_sink_data}
""".format(
	eth_source_stb=io_name("eth", "source_stb"),
	eth_source_ack=io_name("eth", "source_ack"),
	eth_source_data=io_name("eth", "source_data"),

	eth_sink_stb=io_name("eth", "sink_stb"),
	eth_sink_ack=io_name("eth", "sink_ack"),
	eth_sink_data=io_name("eth", "sink_data"),
	)
	except:
		pass

	content = ""
	f = open(template, "r")
	done = False
	for l in f:
		content += l
		if "/* ios */" in l and not done:
			content += ios
			done = True

	f.close()
	tools.write_to_file("dut_tb.cpp", content)

def _build_sim(platform, vns, build_name, include_paths, sim_path, serial, verbose):
	include = ""
	for path in include_paths:
		include += "-I"+path+" "

	build_script_contents = """# Autogenerated by mibuild
	rm -rf obj_dir/
verilator {disable_warnings} -O3 --cc dut.v --exe dut_tb.cpp -LDFLAGS "-lpthread" -trace {include}
make -j -C obj_dir/ -f Vdut.mk Vdut

""".format(
	disable_warnings="-Wno-fatal",
	include=include)
	build_script_file = "build_" + build_name + ".sh"
	tools.write_to_file(build_script_file, build_script_contents, force_unix=True)

	_build_tb(platform, vns, serial, os.path.join("..", sim_path,"dut_tb.cpp"))
	if verbose:
		r = subprocess.call(["bash", build_script_file])
	else:
		r = subprocess.call(["bash", build_script_file], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
	if r != 0:
		raise OSError("Subprocess failed")

def _run_sim(build_name):
	run_script_contents = """obj_dir/Vdut
"""
	run_script_file = "run_" + build_name + ".sh"
	tools.write_to_file(run_script_file, run_script_contents, force_unix=True)
	r = subprocess.call(["bash", run_script_file])
	if r != 0:
		raise OSError("Subprocess failed")

class SimVerilatorToolchain:
	# XXX fir sim_path
	def build(self, platform, fragment, build_dir="build", build_name="top",
			sim_path="../migen/mibuild/sim/", serial="console",
			run=True, verbose=False):
		tools.mkdir_noerror(build_dir)
		os.chdir(build_dir)

		if not isinstance(fragment, _Fragment):
			fragment = fragment.get_fragment()
		platform.finalize(fragment)

		v_output = platform.get_verilog(fragment)
		named_sc, named_pc = platform.resolve_signals(v_output.ns)
		v_output.write("dut.v")

		include_paths = []
		for source in platform.sources:
			path = os.path.dirname(source[0]).replace("\\", "\/")
			if path not in include_paths:
				include_paths.append(path)
		include_paths += platform.verilog_include_paths
		_build_sim(platform, v_output.ns, build_name, include_paths, sim_path, serial, verbose)

		if run:
			_run_sim(build_name)

		os.chdir("..")

		return v_output.ns
