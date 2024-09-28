# wayback-custom-view

This project maintains custom views for the Internet Archive WayBack Machine.

## Development

Create a virtual env with Python>=3.8, and run "editable" install.
```
$ pyenv virtualenv system wayback-custom-view
...
$ pyenv local wayback-custom-view
$ pip install -e .[dev]
...
```

Launch test server
```
$ python -m test_server
 * Running on http://localhost:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 123-456-789
 ```

 Open http://localhost:5000/ with a browser.
 