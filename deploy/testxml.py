import argparse
from xmldiff import main, formatting

parser = argparse.ArgumentParser(description='Compares 3 XML file and tests wheirs diff')

parser.add_argument('--local', help='local file', type=str)
parser.add_argument('--remote', help='remote file', type=str)
parser.add_argument('--base', help='base file', type=str)

args = parser.parse_args()

diff = main.diff_files(args.local, args.remote, diff_options={'F': 0.5, 'ratio_mode': 'fast'})

count = diff.count()