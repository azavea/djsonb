# A fork of django-pgjson

PostgreSQL jsonb support for Django.

This renamed fork maintains the field definitions of the excellent
[django-pgjson](https://github.com/djangonauts/django-pgjson) and
reimagines the lookup syntax to provide Django's ORM with Postgres JsonB
filters that can be arbitrarily nested and which are syntactically
lightweight.

## Testing
To run the tests, just ensure that you have docker installed (and
docker-machine if you're on OSX).

The Docker setup will build an image with Python 2.7 installed, along with
all of this project's dependencies. Build the image and launch the
container with [`docker-compose`](https://docs.docker.com/compose/):

```bash
$ docker-compose build
$ docker-compose run test
```

## Installation and use

Setting up djsonb is as simple as defining a model that uses one of its fields:
```python
from django.db import models
from djsonb import fields as jsb

class Person(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    other_stuff = jsb.JsonBField()
```

We can then do some neat stuff like:
```python
// Find people from Hays, Kansas
Person.objects.filter(other_stuff__jsonb={'other_stuff': {'home_town': {'State': {'_rule_type': 'containment', 'contains': ['Kansas']}, 'City': {'_rule_type': 'containment', 'contains': ['Hays']}}}})
```
