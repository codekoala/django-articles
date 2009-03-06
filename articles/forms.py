from django import forms
from django.forms.fields import email_re
from captcha import CaptchaField

class SendArticleForm(forms.Form):
    name = forms.CharField(label='Your Name')
    email = forms.EmailField(label='Your E-mail Address')
    recipients = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}),
                                 help_text='Please enter the e-mail address for each person you wish to receive this article.  Separate each address with a comma.')
    message = forms.CharField(label='Personalized Message', widget=forms.Textarea,
                              required=False, help_text="If you'd like to add a little personal touch to the message sent to the recipient(s), enter it here.")
    security_code = CaptchaField()

    def clean_recipients(self):
        value = self.cleaned_data['recipients']
        receivers = value.split(',')

        for r in receivers:
            r = r.strip()
            if not email_re.search(r):
                raise forms.ValidationError('Please verify that each e-mail address is valid.  It appears that "%s" is invalid.' % r)

        return value
