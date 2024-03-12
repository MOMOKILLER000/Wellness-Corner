from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User, Allergy
from .models import PendingProduct, Product, ApiProduct, Post, Subscriber
from itertools import chain
from .models import MealProduct, MealApiProduct, UserProfile, Comment, Recipe
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth import authenticate

class RegistrationForm(UserCreationForm):

    allergies = forms.ModelMultipleChoiceField(
        queryset=Allergy.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Allergies",
        help_text="Select your allergies."
    )

    class Meta:
        model = User
        fields = ['email', 'name', 'password1', 'password2', 'allergies']

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
        fields = ['product_name', 'brands', 'quantity', 'categories', 'image', 'protein_per_100g', 'carbs_per_100g', 'fats_per_100g', 'sugars_per_100g', 'sodium_per_100g', 'saturated_fats_per_100g', 'kcal_per_100g', 'price', 'product_type', 'allergies']
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
    

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['user', 'product_type', 'object_id', 'content_type', 'title', 'content']

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['product_type'].widget = forms.Select(choices=Post.PRODUCT_CHOICES)

        # Customize the widget for the object_id field based on product_type
        self.fields['object_id'].widget = forms.Select(choices=[])  # Empty choices initially

        # Optionally, you can add JavaScript to dynamically update the choices based on product_type

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
    allergies = forms.ModelMultipleChoiceField(
        queryset=Allergy.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Allergies",
        help_text="Select your allergies."
    )

    class Meta:
        model = User
        fields = ['name', 'allergies']

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
        fields = ['image', 'name', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 8}),  # Adjust rows as needed
        }