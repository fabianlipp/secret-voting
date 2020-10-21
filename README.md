# Setup

```
git clone https://github.com/fabianlipp/secret-voting/
cd secret-voting
./prepare.sh
cp docker-compose.yml{.tpl,}
cp vote-registration/settings.json{.tpl,}
# edit settings
docker-compose build && docker-compose up -d
```

## Localization

Translate text via Babel. To translate a string within the html templates, use ```{{ _('Text to translate') }}```.

Execute these commands in the subfolder ballot-box / vote-registration if new strings to translate are added:

- Extracting message strings from html files:

    ```pybabel extract -F babel.cfg -k _l -o messages.pot .```
 
- Create a new german messages.po from general messages (**overwrites** existing translations)

    ```pybabel init -i messages.pot -d translations -l de```

- Update german messages.po from general messages

    ```pybabel update -i messages.pot -d translations```

- Compile translations to .mo

    ```pybabel compile -d translations```


# Vote Registration

## Configuration

The SAML ACS expects the Attributes `userid`, `fullname`, `is_voting` (opt.), `is_admin` (opt.), `is_presenter` (opt.)

## Usage

You can watch three different views:

- voter `<url>/`
- election officer `<url>/admin`
- presentation `<url>/presenter`

## Local Mode

By setting `security` / `localMode` `true` in `settings.json` you can bypass the SAML login to test your changes locally.

# Ballot Box

## Usage

t.b.d


# Other comments

This script is based on the example code by Flask-SocketIO (https://github.com/miguelgrinberg/Flask-SocketIO).
