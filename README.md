# DataFabric Security Components

A custom security manager for use with [Apache
Airflow][Airflow] inside the [Datafabric Platform].

This [Security Manager] will validate the JWT tokens from the Datafabric
environment and automatically create or update the user record as appropriate.


This file won't exist until you've run the Airflow webserver at least once in RBAC mode:

```
AIRFLOW__WEBSERVER__RBAC=true
airflow webserver --help
```

## More readings

[Airflow]: https://airflow.apache.org/
[Security Manager]: https://flask-appbuilder.readthedocs.io/en/latest/security.html#your-custom-security
