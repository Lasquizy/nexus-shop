

from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)], attrs={
                'class': 'w-full p-3 rounded-xl border border-gray-300 dark:bg-gray-700 dark:border-gray-600'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'w-full p-4 rounded-xl border border-gray-300 dark:bg-gray-700 dark:border-gray-600',
                'rows': 4,
                'placeholder': 'Partagez votre expérience...'
            }),
        }