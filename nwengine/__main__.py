from nwengine.db import Database
from nwengine.cpu_profile import CpuProfile
from nwengine.error import EngineError
from nwengine.power_profile import PowerProfile
from nwengine.report import Report
from nwengine.config import Config
import argparse
import logging
import sys

def create_cli_parser():
    parser = argparse.ArgumentParser(description='internal argument interface for nodewatts')
    parser.add_argument('--internal_db_addr', type=str, default='localhost')
    parser.add_argument('--internal_db_port', type=int, default=27017)
    parser.add_argument('--export_raw', type=bool, default=False, required=False)
    parser.add_argument('--out_db_addr', type=str, default='localhost', required=False)
    parser.add_argument('--out_db_port', type=int, default=27017, required=False)
    parser.add_argument('--out_db_name', type=str, default="nodewatts", required=False)
    parser.add_argument('--profile_id', type=str, required=True)
    parser.add_argument('--report_name', type=str, required=True)
    parser.add_argument('--sensor_start', type=int, required=True)
    parser.add_argument('--sensor_end', type=int, required=True)
    parser.add_argument('--verbose', type=bool, required=False, default=False)
    return parser

def run_engine(args: Config or dict) -> None:
    if not isinstance(args, Config):
        config = Config(args)

    FORMAT = '%(asctime)s %(clientip)-15s %(user)-8s :Engine: %(message)s'
    if config.verbose:
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        logging.basicConfig(level=logging.INFO, format=FORMAT)

    db = Database(config.internal_db_addr, config.internal_db_port)
    if config.export_raw:
        db.connect_to_export_db(config.out_db_addr, config.out_db_port, config.out_db_name)

    # Calling program will ensure that these collections are not empty before starting engine
    prof_raw = db.get_cpu_prof_by_id(config.profile_id)
    cpu = CpuProfile(prof_raw)

    if config.sensor_start and config.sensor_end:
        power_sample_start = config.sensor_start
        power_sample_end = config.sensor_end
    else:
        # May delete this fallback with further testing, more of a hack for development
        power_sample_start = cpu.start_time - 2000
        power_sample_end = cpu.end_time + 2000

    if power_sample_start > cpu.start_time or power_sample_end < cpu.end_time:
        raise EngineError("Insufficient sensor data to compute power report.")

    power_raw = db.get_power_samples_by_range(power_sample_start, power_sample_end)
    power = PowerProfile(power_raw)
    report = Report(config.report_name, cpu, power)
    formatted = report.to_json()
    db.save_report_to_internal(formatted)

    if config.export_raw:
        db.export_report(formatted)

    logging.info("Data processing complete.")



if __name__ == "__main__":
    config = Config()
    parser = create_cli_parser()
    parser.parse_args(namespace=config)
    run_engine(config)
    sys.exit(0)