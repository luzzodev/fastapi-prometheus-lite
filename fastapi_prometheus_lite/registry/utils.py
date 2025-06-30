"""
FastApiPrometheusLite

'generate_latest' function comes directly from Prometheus Python Client. Has been changed to add only static_labels.

Credits:
- Prometheus Python Client (https://github.com/prometheus/client_python)

"""


from typing import Dict, List, Optional
from prometheus_client import CollectorRegistry, REGISTRY, utils


def generate_latest(registry: CollectorRegistry = REGISTRY, static_labels: Optional[Dict[str, str]] = None) -> bytes:
    """Returns the metrics from the registry in latest text format as a string."""

    static_labels: Dict[str, str] = static_labels or {}
    def sample_line(line):
        merged_labels: Dict[str, str] = dict(line.labels)
        merged_labels.update(static_labels)

        if merged_labels:
            labelstr = '{{{0}}}'.format(','.join(
                ['{}="{}"'.format(
                    k, v.replace('\\', r'\\').replace('\n', r'\n').replace('"', r'\"'))
                    for k, v in sorted(merged_labels.items())]))
        else:
            labelstr = ''
        timestamp = ''
        if line.timestamp is not None:
            # Convert to milliseconds.
            timestamp = f' {int(float(line.timestamp) * 1000):d}'
        return f'{line.name}{labelstr} {utils.floatToGoString(line.value)}{timestamp}\n'

    output = []
    for metric in registry.collect():
        try:
            mname = metric.name
            mtype = metric.type
            # Munging from OpenMetrics into Prometheus format.
            if mtype == 'counter':
                mname = mname + '_total'
            elif mtype == 'info':
                mname = mname + '_info'
                mtype = 'gauge'
            elif mtype == 'stateset':
                mtype = 'gauge'
            elif mtype == 'gaugehistogram':
                # A gauge histogram is really a gauge,
                # but this captures the structure better.
                mtype = 'histogram'
            elif mtype == 'unknown':
                mtype = 'untyped'

            output.append('# HELP {} {}\n'.format(
                mname, metric.documentation.replace('\\', r'\\').replace('\n', r'\n')))
            output.append(f'# TYPE {mname} {mtype}\n')

            om_samples: Dict[str, List[str]] = {}
            for s in metric.samples:
                for suffix in ['_created', '_gsum', '_gcount']:
                    if s.name == metric.name + suffix:
                        # OpenMetrics specific sample, put in a gauge at the end.
                        om_samples.setdefault(suffix, []).append(sample_line(s))
                        break
                else:
                    output.append(sample_line(s))
        except Exception as exception:
            exception.args = (exception.args or ('',)) + (metric,)
            raise

        for suffix, lines in sorted(om_samples.items()):
            output.append('# HELP {}{} {}\n'.format(metric.name, suffix,
                                                    metric.documentation.replace('\\', r'\\').replace('\n', r'\n')))
            output.append(f'# TYPE {metric.name}{suffix} gauge\n')
            output.extend(lines)
    return ''.join(output).encode('utf-8')
