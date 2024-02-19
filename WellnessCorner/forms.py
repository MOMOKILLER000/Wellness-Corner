from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Allergy

class RegistrationForm(UserCreationForm):
    is_client = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check this box if you are a client."
    )

    allergies = forms.ModelMultipleChoiceField(
        queryset=Allergy.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Allergies",
        help_text="Select your allergies."
    )

    class Meta:
        model = User
        fields = ['email', 'name', 'password1', 'password2', 'is_client', 'allergies']

class AllergyForm(forms.ModelForm):
    class Meta:
        model = Allergy
        fields = ['name']
