from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Allergy
from .models import PendingProduct, Product

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

class ProductForm(forms.ModelForm):
    class Meta:
        model = PendingProduct
        fields = ['product_name', 'brands', 'quantity', 'categories', 'image', 'protein_per_100g', 'carbs_per_100g', 'fats_per_100g', 'kcal_per_100g', 'price', 'product_type', 'allergies']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'}),  # Add an accept attribute to limit file types to images
        }

    def clean(self):
        cleaned_data = super().clean()
        product_name = cleaned_data.get("product_name")
        if Product.objects.filter(product_name=product_name).exists():
            raise forms.ValidationError("Product already exists.")
        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image', False)
        if not image:
            raise forms.ValidationError("Image is required.")
        return image