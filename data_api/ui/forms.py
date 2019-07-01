from django import forms


class OrgForm(forms.Form):
    api_key = forms.CharField(required=True)
    server = forms.CharField(required=True, initial='https://app.rapidpro.io')
