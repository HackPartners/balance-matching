# Testing
Testing the cloud function locally:
Call `./scripts/run_local_http.sh` which will start local listener for the cloud function.

Once the above script is running call `./tests/test.py` which will send request and print success if it succeeds.

Testing the with the deployed cloud function, the URL will need to be changed.

To Debug the function you may evoke functions-framework from your debugger (pycharm settings described):
- script path: `./venv/bin/functions_framework`
- parameters: `--source=src/main.py --target=filter_geojson --signature-type=http --port=4000 --debug`
- environment variable: `PYTHONUNBUFFERED=1`
- working directory: `./`

