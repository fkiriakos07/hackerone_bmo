# hackerone_bmo
A script to copy reports from HackerOne to Bugzilla.

## Create a venv in the current directory
1. `python3 -m venv ./hackerone_bmo`
2. `source ./hackerone_bmo/bin/activate`
3. `python3 -m pip install -U pip`

## Install Dependencies
1. `python3 -m pip install click rich requests`
2. `python3 -m pip install git+https://github.com/python-bugzilla/python-bugzilla.git`

## Usage
- `python3 ./h1-cli.py --help`
```
Usage: h1-cli.py [OPTIONS] COMMAND [ARGS]...

Options:
  -h1u, --h1-key-username TEXT  HackerOne API key name  [required]
  --cache                       Cache reports when possible
  --cache-path FILE             Where the cache should be saved  [default:
                                /tmp/h1_cache]
  --help                        Show this message and exit.

Commands:
  show        Print H1 report to screen with the correct formatting
  upload-bmo  Upload a HackerOne report to Bugzilla
```

## Example Command
### Create a ticket on the bugzilla instance
- `python3 h1-cli.py upload-bmo <H1 ticket ID>`
### Just format and display a HackerOne report without uploading
- `python3 h1-cli.py show <H1 ticket ID>`

# Credit
- Heavily based on the work by [thiezn](https://gist.github.com/thiezn/eeb78dcdc3902cdb2f33f9050d6d429d). Thank you.
