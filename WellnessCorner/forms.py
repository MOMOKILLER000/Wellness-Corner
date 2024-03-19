from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User, Allergy
from .models import PendingProduct, Product, ApiProduct, Post, Subscriber
from itertools import chain
from .models import MealProduct, MealApiProduct, UserProfile, Comment, Recipe
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth import authenticate

class RegistrationForm(UserCreationForm):
    diet = forms.ChoiceField(choices=User.PREFERRED_DIET_CHOICES, initial='None')
    allergies = forms.ModelMultipleChoiceField(
        queryset=Allergy.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Allergies",
        help_text="Select your allergies."
    )

    class Meta:
        model = User
        fields = ['email', 'name', 'password1', 'password2', 'diet', 'allergies']

class LoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class AllergyForm(forms.ModelForm):
    class Meta:
        model = Allergy
        fields = ['name']

class ProductForm(forms.ModelForm):
    class Meta:
        model = PendingProduct
        fields = ['product_name', 'brands', 'quantity', 'categories', 'image','ean_code', 'protein_per_100g', 'carbs_per_100g', 'fats_per_100g', 'sugars_per_100g', 'sodium_per_100g', 'saturated_fats_per_100g', 'kcal_per_100g', 'price', 'allergies', 'is_vegan', 'is_vegetarian']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        required_fields = ['product_name', 'brands', 'quantity', 'categories', 'image', 'protein_per_100g', 'carbs_per_100g', 'fats_per_100g', 'sugars_per_100g', 'sodium_per_100g', 'saturated_fats_per_100g', 'kcal_per_100g', 'price']
        for field_name in required_fields:
            self.fields[field_name].required = True

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

    def clean_ean_code(self):
        ean_code = self.cleaned_data.get('ean_code')
        if not ean_code.isdigit() or len(ean_code) != 13:
            raise forms.ValidationError("EAN code must be exactly 13 digits long and contain only numbers.")
        return ean_code

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['user', 'product_type', 'object_id', 'content_type', 'title', 'content']

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['product_type'].widget = forms.Select(choices=Post.PRODUCT_CHOICES)

        
        self.fields['object_id'].widget = forms.Select(choices=[])  

        

    def set_product_choices(self, product_type):
        if product_type == 'Product':
            products = Product.objects.all()
        elif product_type == 'ApiProduct':
            products = ApiProduct.objects.all()
        else:
            products = []

        self.fields['object_id'].queryset = products


class NewsletterSubscriptionForm(forms.Form):
    def save_subscription(self, user):
        email = user.email
        Subscriber.objects.get_or_create(email=email)

class EmailSubscriberForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)

class ContactForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)

class MealProductForm(forms.ModelForm):
    class Meta:
        model = MealProduct
        fields = ['product', 'quantity_grams']

class MealApiProductForm(forms.ModelForm):
    class Meta:
        model = MealApiProduct
        fields = ['api_product', 'quantity_grams']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['age', 'height', 'weight','gender', 'activity_level', 'goal']

class UserAccountForm(forms.ModelForm):
    diet = forms.ChoiceField(choices=User.PREFERRED_DIET_CHOICES, initial='None')
    allergies = forms.ModelMultipleChoiceField(
        queryset=Allergy.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Allergies",
        help_text="Select your allergies."
    )

    class Meta:
        model = User
        fields = ['name', 'allergies', 'diet']

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Old Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['old_password', 'new_password1', 'new_password2']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['image', 'name', 'description', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 8}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'small-textarea'}),  
        }