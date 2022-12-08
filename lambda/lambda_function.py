import logging
import ask_sdk_core.utils as ask_utils
import json
from ask_sdk_model.interfaces.alexa.presentation.apl import (
    RenderDocumentDirective)

import os
import boto3
import json
import ask_sdk_core
import util
import periodFunctions

from ask_sdk.standard import StandardSkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from ask_sdk_core.dispatch_components import AbstractRequestInterceptor
from ask_sdk_core.dispatch_components import AbstractResponseInterceptor


# El valor de PERIOD_TRACKING está a True si mantienes un registro del periodo. El valor de VISIT_TRACKING está a True si cuentas cada visita que tiene la persona.
PERIOD_TRACKING = True
VISIT_TRACKING = True


from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.dialog import ElicitSlotDirective

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        device_id = handler_input.request_envelope.context.system.device.device_id

        user_time_zone = ""
        greeting = ""

        try:
            user_preferences_client = handler_input.service_client_factory.get_ups_service()
            user_time_zone = user_preferences_client.get_system_time_zone(device_id)
        except Exception as e:
            user_time_zone = 'error.'
            logger.error(e)

        if user_time_zone == 'error':
            greeting = 'Hello.'
        else:
            # get the hour of the day or night in your customer's time zone
            from periodFunctions import get_hour
            hour = get_hour(user_time_zone)
            if 0 <= hour and hour <= 4:
                greeting = "Hi night-owl!"
            elif 5 <= hour and hour <= 11:
                greeting = "Good morning!"
            elif 12 <= hour and hour <= 17:
                greeting = "Good afternoon!"
            elif 17 <= hour and hour <= 23:
                greeting = "Good evening!"
            else:
                greeting = "Howdy partner!"


        speak_output = ''
        session_attributes = handler_input.attributes_manager.session_attributes

        if session_attributes["visits"] == 0:
            speak_output = f"{greeting} Welcome to Droplet. Your skill for menstruation and birth control recording and organization. " \
                f"I need your last period date. "
        else:
            speak_output = f"{greeting} Welcome back to Droplet! " \
                f"What do you need?"

        # increment the number of visits and save the session attributes so the
        # ResponseInterceptor will save it persistently.
        session_attributes["visits"] = session_attributes["visits"] + 1


        #====================================================================
        # Add a visual with Alexa Layouts
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Set a headline and subhead to display on the screen if there is one
                                #====================================================================
                                "Title": 'Tell me your last period date',
                                "Subtitle": 'Welcome to DropLet.',
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#CONSEGUIR EL PERIODO Y DURACION
class GetFullPeriodIntentHandler(AbstractRequestHandler):
    """Handler para el Intent GetFullPeriodIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        
        return (
            ask_utils.is_intent_name("GetFullPeriodIntent")(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
 #       if session_attributes["current_period"] == None:
        # si hay un atributo de periodo actual pero está vacío, o si no hay ningún error, se le pide que te digan el periodo

        # Se obtienen los valores de los slots
        year = ask_utils.request_util.get_slot(handler_input, "year").value
        month = ask_utils.request_util.get_slot(handler_input, "month").value
        day = ask_utils.request_util.get_slot(handler_input, "day").value
        duration = ask_utils.request_util.get_slot(handler_input, "duration").value
        
        # Se comprueba la respuesta dada
        from periodFunctions import check_answer
        answer = check_answer(
            day,
            month,
            year,
            duration
        )
            
        #importamos una función que permite pasar a una fecha String la fecha del periodo
        from periodFunctions import translate_to_datetime
        dt = translate_to_datetime(day, month, year)
            
        from periodFunctions import datetime_to_string
        dt_string= datetime_to_string(dt)
        
        #se guarda en last_period el string de la fecha obtenida
        session_attributes["last_period"] = dt_string
        
        #guardamos por otro lado la variable duration
        from periodFunctions import int_to_str
        duration_str = int_to_str(duration)
        
        session_attributes["duration"] = duration_str
        
        # Se añade el periodo al valor de periodo actual
        # Guarda el valor para el resto de la función,
        # y ajusta el periodo actual como vacío
        session_attributes["current_period"] = session_attributes["last_period"]
            
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''

        # Si las repsuestas son aceptadas:
        if answer:
            title = 'Thanks for the information'
            subtitle = 'It has been saved correctly'
            speak_output = f"Thank you. Your period has been saved correctly. You can ask me when your next period will be, add a new one or you can also add a birth control pill record. Ask for help if you need more information about it."
        else:
            title = 'I did not get it'
            subtitle = 'Could you repeat?'
            speak_output = f"Sorry. I didn't get the information. " \
                f"Could you repeat again?"

        # guarda todos los datos actualizados de la sesión
        handler_input.attributes_manager.session_attributes = session_attributes
        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )



#CUANDO TE PIDE LA PETICION PARA AÑADIR UNA PASTILLA ANTICONCEPTIVA
class GetBirthPillIntentHandler(AbstractRequestHandler):
    """Handler para el Intent GetBirthPillIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("GetBirthPillIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
        if session_attributes["birthPillTime"] == []:
            title = 'Tell me the time you usually take the pill'
            subtitle = 'This will help me to remind you in the future'
            speak_output = f"Ok. I will need you to tell me the time you usually take the pill in order to give you a best experience. "
        else:
            title = 'Tell me again the time you usually take the pill'
            subtitle = 'This will help me to remind you in the future'
            speak_output = f"Ok. I will need you to tell again me the time you usually take the pill in order to give you a best experience. "


        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )



#TE DICE LA HORA PARA AÑADIR LA PASTILLA
class AddBirthPillIntentHandler(AbstractRequestHandler):
    """Handler para el Intent AddBirthPillIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        
        return (
            ask_utils.is_intent_name("AddBirthPillIntent")(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes


        # Se obtienen los valores de los slots
        time = ask_utils.request_util.get_slot(handler_input, "time").value
        
        from periodFunctions import check_time
        answer = check_time(
            time
        )
        
#        from periodFunctions import datetime_to_string_pill
#        time_string= datetime_to_string_pill(time)
        
        #se guarda en last_period el string de la fecha obtenida
        session_attributes["birthPillTime"] = time
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''

        # Si las repsuestas son aceptadas:
        if answer:
            title = 'Thanks for the information'
            subtitle = 'It has been saved correctly'
            speak_output = f"Thank you so much. I will remind you to take the pill at {time}"
        else:
            title = 'I did not get it'
            subtitle = 'Could you repeat?'
            speak_output = f"Sorry. I didn't get the information. " \
                f"Could you repeat again?"

        # guarda todos los datos actualizados de la sesión
        handler_input.attributes_manager.session_attributes = session_attributes
        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )



#CUANDO TE PIDE EL SIGUIENTE PERIODO
class NextPeriodIntentHandler(AbstractRequestHandler):
    """Handler para el Intent NextPeriodIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("NextPeriodIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = ''
        
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
        sdt = session_attributes["current_period"]
        nextPeriod = ''
        
        if session_attributes["current_period"] != []:
            from periodFunctions import string_to_datetime
            date_datetime = string_to_datetime(sdt)
            from periodFunctions import calculate_next_period
            nextPeriod_dt = calculate_next_period(date_datetime)
            from periodFunctions import datetime_to_string
            nextPeriod = datetime_to_string(nextPeriod_dt)
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        
        if session_attributes["current_period"] == []:
        # comprueba si hay ahora mismo un periodo actual. Si no lo hay, te pide que se lo digas
            title = f'Sorry, you do not have any period records.'
            subtitle = 'Do you want to know anything else?'
            speak_output = f"Sorry, you don't have any period records. Try to say Add new period."
        else:
            title = f'Your next period will be {nextPeriod}'
            subtitle = 'Do you want to know anything else?'
            speak_output = f"Your next period will be {nextPeriod}. "


        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#AÑADIR NUEVO PERIODO
class AddNewPeriodIntentHandler(AbstractRequestHandler):
    """Handler para el Intent AddNewPeriodIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("AddNewPeriodIntent")(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
            # si hay un atributo de periodo actual pero está vacío, o si no hay ningún error, se le pide que te digan el periodo

        # Se obtienen los valores de los slots
        year = ask_utils.request_util.get_slot(handler_input, "year").value
        month = ask_utils.request_util.get_slot(handler_input, "month").value
        day = ask_utils.request_util.get_slot(handler_input, "day").value
        duration = ask_utils.request_util.get_slot(handler_input, "duration").value
            
        # Se comprueba la respuesta dada
        from periodFunctions import check_answer
        answer = check_answer(
            day,
            month,
            year,
            duration
        )
            
        #importamos una función que permite pasar a una fecha String la fecha del periodo
        from periodFunctions import translate_to_datetime
        dt = translate_to_datetime(day, month, year)
            
        from periodFunctions import datetime_to_string
        dt_string= datetime_to_string(dt)
            
        #se guarda en last_period el string de la fecha obtenida
        session_attributes["last_period"] = dt_string
        
        #guardamos por otro lado la variable duration
        from periodFunctions import int_to_str
        duration_str = int_to_str(duration)
            
        session_attributes["duration"] = duration_str
            
        # Se añade el periodo al valor de periodo actual
        # Guarda el valor para el resto de la función,
        # y ajusta el periodo actual como vacío
        session_attributes["current_period"] = session_attributes["last_period"]
            
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''

        # Si las repsuestas son aceptadas:
        if answer:
            title = 'Thanks for the information'
            subtitle = 'It has been saved correctly.'
            speak_output = f"Great, your new last period has been saved correctly. You can ask me when your next period will be."
        else:
            title = 'I did not get it'
            subtitle = 'Could you repeat?'
            speak_output = f"Sorry. I didn't get the information. " \
                f"Could you repeat again?"

        # guarda todos los datos actualizados de la sesión
        handler_input.attributes_manager.session_attributes = session_attributes
        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#BORRAR REGISTRO DE LA PASTILLA ANTICONCEPTIVA
class DeleteBirthPillRecordIntentHandler(AbstractRequestHandler):
    """Handler para el Intent DeleteBirthPillRecordIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("DeleteBirthPillRecordIntent")(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
        
        #si el atributo no está vacío:
        if session_attributes["birthPillTime"] != []:
            
            #lo ponemos para que esté vacío
            session_attributes["birthPillTime"] = []

            
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''

        # Si no está vacío el birthPillTime
        if session_attributes["birthPillTime"] == []:
            title = 'I have removed it correctly.'
            subtitle = 'If you want to add it another time, just say it'
            speak_output = f"I have removed it correctly. If you want to add a birth pill record, just say it"
        else:
            title = 'I did not get it'
            subtitle = 'Try again in other moment'
            speak_output = f"Sorry, there was a problem and I couldn't remove it correctly."

        # guarda todos los datos actualizados de la sesión
        handler_input.attributes_manager.session_attributes = session_attributes
        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )



#PEDIR LA HORA DE LA PASTILLA ANTICONCEPTIVA
class BirthPillInfoIntentHandler(AbstractRequestHandler):
    """Handler para el Intent BirthPillInfoIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("BirthPillInfoIntent")(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
            
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        birthPillTime = session_attributes["birthPillTime"]

        # Si está vacío el birthPillTime
        if session_attributes["birthPillTime"] == []:
            title = 'You do not have any records.'
            subtitle = 'If you want to add the time, just say: Add pill record.'
            speak_output = f"Sorry, right now you don't have any records. Try to say: add pill record. After adding the time, you can ask me whenever you want."
        else:
            title = f'You are taking the birth control pill at {birthPillTime}.'
            subtitle = 'Do not forget to take it at your time!'
            speak_output = f"You are taking the birth control pill at {birthPillTime}."

        # guarda todos los datos actualizados de la sesión
        handler_input.attributes_manager.session_attributes = session_attributes
        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#PARA SABER EL DÍA DE OVULACIÓN O DÍA MÁS FÉRTIL
class FertileDayIntentHandler(AbstractRequestHandler):
    """Handler para el Intent FertileDayIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("FertileDayIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = ''
        
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
        sdt = session_attributes["current_period"]
        fertileDay = ''
        
        if session_attributes["current_period"] != []:
            from periodFunctions import string_to_datetime
            date_datetime = string_to_datetime(sdt)
            from periodFunctions import calculate_fertile_day
            fertileDay_dt = calculate_fertile_day(date_datetime)
            from periodFunctions import datetime_to_string
            fertileDay = datetime_to_string(fertileDay_dt)
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        if session_attributes["current_period"] == []:
        # comprueba si hay ahora mismo un periodo actual. Si no lo hay, te pide que se lo digas
            title = f'Sorry, you do not have any period records.'
            subtitle = 'Do you want to know anything else?'
            speak_output = f"Sorry, you don't have any period records. Try to say Add new period."
        else:
            title = f'Your most fertile day will be the {fertileDay}'
            subtitle = 'Do you want to know anything else?'
            speak_output = f"Your most fertile day will be {fertileDay}. "

        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#CUANDO SE TE OLVIDA TOMARTE LA PASTILLA
class ForgotPillIntentHandler(AbstractRequestHandler):
    """Handler para el Intent ForgotPillIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("ForgotPillIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = ''
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
        title = f'It depends on the type of pill you take and the number of pills you miss. Refer to the information leaflet that comes in the box of your tablets.'
        subtitle = 'Do you want to know anything else?'
        speak_output = "What you should do if you miss a pill depends on 1) the type of pill you take (the combined estrogen and progestin pill or the progestin-only pill) and 2) the number of pills you miss. The information flyer that comes in the box of your pills should include specific instructions on what to do if you miss taking a pill of the brand you use. For further information or having doubts, I recommend to visit your doctor and ask them about it. Do you need anything else?"


        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#PEDIR EL ÚLTIMO PERIODO YA REGISTRADO
class LastPeriodIntentHandler(AbstractRequestHandler):
    """Handler para el Intent LastPeriodIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("LastPeriodIntent")(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        # pilla los atributos de sesión actuales, creando un objeto que se puede leer/actualizar
        session_attributes = handler_input.attributes_manager.session_attributes
            
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        lasPeriod = session_attributes["last_period"]
        duration = session_attributes["duration"]

        # Si está vacío el birthPillTime
        if session_attributes["last_period"] == []:
            title = 'You do not have any records.'
            subtitle = 'If you want to add the time, just say: Add new period.'
            speak_output = f"Sorry, right now you don't have any records. Try to say: add new period. After adding your period, you can ask me whenever you want."
        else:
            title = f'Your last period was {lasPeriod} and it lasted {duration} days.'
            subtitle = 'You can add a new record or ask me for your next period'
            speak_output = f"Your last period was {lasPeriod} and it lasted {duration} days."

        # guarda todos los datos actualizados de la sesión
        handler_input.attributes_manager.session_attributes = session_attributes
        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#SALUDO
class HelloIntentHandler(AbstractRequestHandler):
    """Handler para el Intent HelloIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("HelloIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = ''
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
        title = f'Hello! What do you need?'
        subtitle = 'You can say Help if you do not know what to say'
        speak_output = "Hello! Right now you are in the Skill Droplet, your period and birth control pill recorder. Try to say Next period or Help if you want to know more."


        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


#GRACIAS
class ThanksIntentHandler(AbstractRequestHandler):
    """Handler para el Intent ThanksIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("ThanksIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = ''
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
        title = f'You are very welcome'
        subtitle = 'You can say Help if you do not know what to say'
        speak_output = "Pleasure is mine. If you need anything else, just let me know. I'm happy to help."


        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#OK O CUANDO DICES VALE
class YesIntentHandler(AbstractRequestHandler):
    """Handler para el Intent YesIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = ''
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
        title = f'Need anything else?'
        subtitle = 'You can say Help if you do not know what to say'
        speak_output = "Ok. Do you need anything else?"


        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

#cuando dices NO
class NoIntentHandler(AbstractRequestHandler):
    """Handler para el Intent NoIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        from periodFunctions import period_recorded
        
        return (
            ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)
            and period_recorded(handler_input)
        )
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = ''
        
        # Inicializamos variables para la parte visual (la de la pantalla).
        title = ''
        subtitle = ''
        
        # comprueba si hay ahora mismo un periodo actual. Si lo hay, no te pide esto
        title = f'Need anything else?'
        subtitle = 'You can say Help if you do not know what to say'
        speak_output = "Ok. I'll be here if you need something. If you want to stop the skill just say Stop or Bye."


        
        #====================================================================
        # Añade una manera de que se vea más visual con Alexa Layouts (por si el usuario presenta una Alexa con pantalla)
        #====================================================================

        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(
                    handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                #====================================================================
                                # Proporciona un cabecera y una subcabecera para mostrar en la pantalla si hubiese una
                                #====================================================================
                                "Title": title,
                                "Subtitle": subtitle,
                            }
                        }
                    )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "DropLet is an Alexa Skill made by a Software Engineer student for his Undergraduate Thesis Project. The main purpose of DropLet is to keep a record of your last period and its duration. and get directions if you forget to take your pill. You can also delete your pill time record and add a new date for your next period. As an added bonus, you can also record the time you take your birth control pill. This way, you can ask when your next period is due, your next most fertile day, be reminded when to take your pill, I'm here to offer you peace of mind and security. All in all, you can ask me your last period, your next period, to add a new period, your most fertile day, the time you take your birth control pill, delete the reminder when you take your birth control pill or get information if you forget to take the pill. What do you need?"
        
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input) or
                ask_utils.is_intent_name("ByeIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "See you next time!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure what you have tried to say. You can say Help if you don't know what to say."
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class LoadDataInterceptor(AbstractRequestInterceptor):
    """Check if user is invoking skill for first time and initialize preset."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        session_attributes = handler_input.attributes_manager.session_attributes

        # ensure important variables are initialized so they're used more easily in handlers.
        # This makes sure they're ready to go and makes the handler code a little more readable

        if 'current_period' not in persistent_attributes:
            persistent_attributes["current_period"] = []
            
        if 'current_period' not in session_attributes:
            session_attributes["current_period"] = []
        
        if 'last_period' not in persistent_attributes:
            persistent_attributes["last_period"] = []

        if 'last_period' not in session_attributes:
            session_attributes["last_period"] = []

        if 'duration' not in persistent_attributes:
            persistent_attributes["duration"] = []

        if 'duration' not in session_attributes:
            session_attributes["duration"] = []
        
        if 'birthPillTime' not in persistent_attributes:
            persistent_attributes["birthPillTime"] = []

        if 'birthPillTime' not in session_attributes:
            session_attributes["birthPillTime"] = []
        
        # if you're tracking last_period between sessions, use the persistent value
        # set the visits value (either 0 for new, or the persistent value)
        session_attributes["current_period"] = persistent_attributes["current_period"] if PERIOD_TRACKING else session_attributes["current_period"]
        session_attributes["last_period"] = persistent_attributes["last_period"] if PERIOD_TRACKING else session_attributes["last_period"]
        session_attributes["duration"] = persistent_attributes["duration"] if PERIOD_TRACKING else session_attributes["duration"]
        session_attributes["birthPillTime"] = persistent_attributes["birthPillTime"] if PERIOD_TRACKING else session_attributes["birthPillTime"]
        session_attributes["visits"] = persistent_attributes["visits"] if VISIT_TRACKING else 0 #else 'visits' in persistent_attributes

class LoggingRequestInterceptor(AbstractRequestInterceptor):
    """Log the alexa requests."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.debug('----- REQUEST -----')
        logger.debug("{}".format(
            handler_input.request_envelope.request))


class SaveDataInterceptor(AbstractResponseInterceptor):
    """Save persistence attributes before sending response to user."""
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        session_attributes = handler_input.attributes_manager.session_attributes

        persistent_attributes["current_period"] = session_attributes["current_period"] if PERIOD_TRACKING  else []
        persistent_attributes["last_period"] = session_attributes["last_period"] if PERIOD_TRACKING  else []
        persistent_attributes["duration"] = session_attributes["duration"] if PERIOD_TRACKING  else []
        persistent_attributes["birthPillTime"] = session_attributes["birthPillTime"] if PERIOD_TRACKING  else []
        persistent_attributes["visits"] = session_attributes["visits"]

        handler_input.attributes_manager.save_persistent_attributes()

class LoggingResponseInterceptor(AbstractResponseInterceptor):
    """Log the alexa responses."""
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        logger.debug('----- RESPONSE -----')
        logger.debug("{}".format(response))



# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = StandardSkillBuilder(
    table_name=os.environ.get("DYNAMODB_PERSISTENCE_TABLE_NAME"), auto_create_table=False)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GetFullPeriodIntentHandler())
sb.add_request_handler(GetBirthPillIntentHandler())
sb.add_request_handler(AddBirthPillIntentHandler())
sb.add_request_handler(NextPeriodIntentHandler())
sb.add_request_handler(AddNewPeriodIntentHandler())
sb.add_request_handler(DeleteBirthPillRecordIntentHandler())
sb.add_request_handler(BirthPillInfoIntentHandler())
sb.add_request_handler(FertileDayIntentHandler())
sb.add_request_handler(ForgotPillIntentHandler())
sb.add_request_handler(LastPeriodIntentHandler())
sb.add_request_handler(HelloIntentHandler())
sb.add_request_handler(ThanksIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler())
#sb.add_request_handler(GetPeriodDateIntentHandler())
#sb.add_request_handler(RepeatPeriodDateHandler())
#sb.add_request_handler(GetPeriodDateAgainIntentHandler())
#sb.add_request_handler(GetPeriodDurationIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

# Interceptors
sb.add_global_request_interceptor(LoadDataInterceptor())
sb.add_global_request_interceptor(LoggingRequestInterceptor())

sb.add_global_response_interceptor(SaveDataInterceptor())
sb.add_global_response_interceptor(LoggingResponseInterceptor())

lambda_handler = sb.lambda_handler()