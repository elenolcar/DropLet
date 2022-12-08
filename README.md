# DropLet
This Alexa Skill allows you to keep track of your period and birth control pills. This is an initial project for an Undergraduate Thesis Project that may possibly have errors. Feel free to test, modify and improve the code if you wish.


If you want to try the skill and you don't know how, take a look at the following link from the official Alexa Developer page that explains step by step the requirements to create a custom skill: [Steps to Build a Custom Skill](https://developer.amazon.com/en-US/docs/alexa/custom-skills/steps-to-build-a-custom-skill.html)


## Usage
### First time we open the kill
```
Alexa, open drop let period
    >> Good morning! Welcome to Droplet. Your skill for menstruation and birth control recording and organization. I need your last period date.
November 4, 2022
    >> Thank you so much. Now I need to know the duration of your period in days in order to give you a best experience.
4 days
    >> Having said that, your last period was the 4 of November of 2022, and lasted 4 days, wasn't it?
Yes
    >> Thank you. Your period has been saved correctly. You can ask me when your next period will be, add a new one or you can also add a birth control pill record. Ask for help if you need more information about it.
```
### Next time we open the skill
```
Alexa, open drop let period
    >> Good morning! Welcome back to Droplet! What do you need?
...
```
## Repository Contents
- `lambda` - Back-End Logic for the Alexa Skill hosted on [AWS Lambda](https://aws.amazon.com/lambda/)
- `interactionModels` - Voice User Interface and Language Specific Interaction Models

## Additional Resources
### Documentation
- [Official Alexa Skills Kit Python SDK](https://pypi.org/project/ask-sdk/)
- [Official Alexa Skills Kit Python SDK Docs](https://developer.amazon.com/en-US/docs/alexa/alexa-skills-kit-sdk-for-python/overview.html)
- [Official Alexa Skills Kit Documentation](https://developer.amazon.com/en-US/docs/alexa/ask-overviews/what-is-the-alexa-skills-kit.html)

