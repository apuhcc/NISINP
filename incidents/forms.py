from datetime import datetime
from functools import partial
from operator import is_not

import pytz
from bootstrap_datepicker_plus.widgets import DateTimePickerInput
from django import forms
from django.db.models import Q
from django.forms.widgets import ChoiceWidget
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django_countries import countries
from django_otp.forms import OTPAuthenticationForm

from governanceplatform.helpers import get_active_company_from_session
from governanceplatform.models import Regulation, Regulator, Sector, Service
from governanceplatform.settings import TIME_ZONE

from theme.globals import REGIONAL_AREA
from .models import Answer, Incident, IncidentWorkflow, Question, SectorRegulation


# TO DO: change the templates to custom one
class ServicesListCheckboxSelectMultiple(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "checkbox"
    template_name = "django/forms/widgets/service_checkbox_select.html"
    option_template_name = "django/forms/widgets/service_checkbox_option.html"
    add_id_index = False
    checked_attribute = {"checked": True}
    option_inherits_attrs = False
    initial_data = None

    def __init__(self, *args, **kwargs):
        if "initial" in kwargs:
            self.initial_data = kwargs.pop("initial")
        super().__init__(*args, **kwargs)

    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget."""
        groups = []
        has_selected = False

        for index, (option_value, option_label) in enumerate(self.choices):
            if option_value is None:
                option_value = ""
            subgroup = []
            if isinstance(option_label, (list, tuple)):
                group_name = option_value
                subindex = 0
                choices = option_label
            else:
                group_name = None
                subindex = None
                choices = [(option_value, option_label)]
            groups.append((group_name, subgroup, index))

            # other_choices = []
            for subvalue, sublabel in choices:
                selected = (not has_selected or self.allow_multiple_selected) and str(
                    subvalue
                ) in value
                has_selected |= selected
                # manage default value
                if self.initial_data is not None:
                    if subvalue in self.initial_data:
                        selected = True

                subgroup.append(
                    self.create_option(
                        name,
                        subvalue,
                        sublabel,
                        selected,
                        index,
                        subindex=subindex,
                        attrs=attrs,
                    )
                )

                if subindex is not None:
                    subindex += 1
        return groups


class DropdownCheckboxSelectMultiple(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "select"
    template_name = "django/forms/widgets/dropdown_checkbox_select.html"
    option_template_name = "django/forms/widgets/dropdown_checkbox_option.html"
    option_inherits_attrs = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# Class for Multichoice and single choice
# TO DO : improve layout
class OtherCheckboxSelectMultiple(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "checkbox"
    template_name = "django/forms/widgets/other_checkbox_select.html"
    option_template_name = "django/forms/widgets/other_checkbox_option.html"

    def __init__(self, *args, **kwargs):
        if "input_type" in kwargs:
            self.input_type = kwargs.pop("input_type")
        super().__init__(*args, **kwargs)

    # this is the standard optgroups function, just add a hook to add new input
    # and modify the CSS class
    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget."""
        groups = []
        has_selected = False

        for index, (option_value, option_label) in enumerate(self.choices):
            if option_value is None:
                option_value = ""
            subgroup = []
            if isinstance(option_label, (list, tuple)):
                group_name = option_value
                subindex = 0
                choices = option_label
            else:
                group_name = None
                subindex = None
                choices = [(option_value, option_label)]
            groups.append((group_name, subgroup, index))

            # other_choices = []
            for subvalue, sublabel in choices:
                selected = (not has_selected or self.allow_multiple_selected) and str(
                    subvalue
                ) in value
                has_selected |= selected
                # add CSS class on the one who need additional answer
                # if sublabel.allowed_additional_answer:
                #     attrs["class"] = attrs["class"] + "need-additional-answer"
                subgroup.append(
                    self.create_option(
                        name,
                        subvalue,
                        sublabel,
                        selected,
                        index,
                        subindex=subindex,
                        attrs=attrs,
                    )
                )
                # if option_label.allowed_additional_answer:
                #     other_choices.append(sublabel)
                if subindex is not None:
                    subindex += 1
        return groups


class AuthenticationForm(OTPAuthenticationForm):
    otp_device = forms.CharField(required=False, widget=forms.HiddenInput)
    otp_challenge = forms.CharField(required=False, widget=forms.HiddenInput)


# create a form for each category and add fields which represent questions
class QuestionForm(forms.Form):
    # for dynamicly add question to forms
    def create_question(self, question, incident_workflow=None, incident=None):
        initial_data = []
        field_name = "__question__" + str(question.id)
        if (
            question.question_type == "MULTI"
            or question.question_type == "MT"
            or question.question_type == "SO"
            or question.question_type == "ST"
        ):
            initial_answer = ""
            input_type = "checkbox"
            choices = []
            if question.question_type == "SO" or question.question_type == "ST":
                input_type = "radio"
            if incident_workflow is not None:
                initial_data = list(
                    filter(
                        partial(is_not, None),
                        Answer.objects.values_list("predefined_answers", flat=True)
                        .filter(question=question, incident_workflow=incident_workflow)
                        .order_by("-timestamp"),
                    )
                )
            elif incident is not None:
                initial_data = list(
                    filter(
                        partial(is_not, None),
                        Answer.objects.values_list("predefined_answers", flat=True)
                        .filter(
                            question=question,
                            incident_workflow=incident.get_latest_incident_workflow(),
                        )
                        .order_by("-timestamp"),
                    )
                )
            for choice in question.predefinedanswer_set.all().order_by("position"):
                choices.append([choice.id, choice])
            if question.question_type == "MULTI" or question.question_type == "MT":
                self.fields[field_name] = forms.MultipleChoiceField(
                    required=question.is_mandatory,
                    choices=choices,
                    widget=forms.CheckboxSelectMultiple(
                        attrs={
                            "title": question.tooltip,
                            "data-bs-toggle": "tooltip",
                        },
                    ),
                    label=question.label,
                    initial=initial_data,
                )
            else:
                self.fields[field_name] = forms.MultipleChoiceField(
                    required=question.is_mandatory,
                    choices=choices,
                    widget=OtherCheckboxSelectMultiple(
                        input_type=input_type,
                        attrs={
                            "title": question.tooltip,
                            "data-bs-toggle": "tooltip",
                        },
                    ),
                    label=question.label,
                    initial=initial_data,
                )

            if question.question_type == "MT" or question.question_type == "ST":
                if incident_workflow is not None:
                    answer = Answer.objects.values_list("answer", flat=True).filter(
                        question=question, incident_workflow=incident_workflow
                    )
                elif incident is not None:
                    answer = (
                        Answer.objects.values_list("answer", flat=True)
                        .filter(
                            question=question,
                            incident_workflow=incident.get_latest_incident_workflow(),
                        )
                        .order_by("-timestamp")
                    )
                if len(answer) > 0:
                    if answer[0] != "":
                        initial_answer = list(filter(partial(is_not, ""), answer))[0]
                self.fields[field_name + "_answer"] = forms.CharField(
                    required=question.is_mandatory,
                    widget=forms.TextInput(
                        attrs={
                            "class": "multichoice-input-freetext",
                            "value": str(initial_answer),
                            "title": question.tooltip,
                            "data-bs-toggle": "tooltip",
                        }
                    ),
                    label="Add precision",
                )
        elif question.question_type == "DATE":
            initial_data = ""
            answer = None
            if incident_workflow is not None:
                answer = (
                    Answer.objects.values_list("answer", flat=True)
                    .filter(question=question, incident_workflow=incident_workflow)
                    .first()
                )
            elif incident is not None:
                answer = (
                    Answer.objects.values_list("answer", flat=True)
                    .filter(
                        question=question,
                        incident_workflow=incident.get_latest_incident_workflow(),
                    )
                    .order_by("-timestamp")
                    .first()
                )
            if answer is not None:
                if answer != "":
                    initial_data = answer
                    initial_data = datetime.strptime(initial_data, "%Y-%m-%d %H:%M")
            self.fields[field_name] = forms.DateTimeField(
                widget=DateTimePickerInput(
                    options={
                        "maxDate": datetime.today().strftime("%Y-%m-%d 23:59:59"),
                    },
                    attrs={
                        "title": question.tooltip,
                        "data-bs-toggle": "tooltip",
                    },
                ),
                required=question.is_mandatory,
                initial=initial_data,
                help_text=gettext_lazy("Date Format YYYY-MM-DD HH:MM"),
            )
            self.fields[field_name].label = question.label
        elif question.question_type == "FREETEXT":
            initial_data = ""
            if incident_workflow is not None:
                answer = Answer.objects.values_list("answer", flat=True).filter(
                    question=question, incident_workflow=incident_workflow
                )
                if len(answer) > 0:
                    if answer[0] != "":
                        initial_data = list(filter(partial(is_not, ""), answer))[0]
            elif incident is not None:
                answer = (
                    Answer.objects.values_list("answer", flat=True)
                    .filter(
                        question=question,
                        incident_workflow=incident.get_latest_incident_workflow(),
                    )
                    .order_by("-timestamp")
                    .first()
                )
                if answer is not None:
                    if answer != "":
                        initial_data = answer

            self.fields[field_name] = forms.CharField(
                required=question.is_mandatory,
                widget=forms.Textarea(
                    attrs={
                        "rows": 3,
                        "title": question.tooltip,
                        "data-bs-toggle": "tooltip",
                    }
                ),
                initial=str(initial_data),
                label=question.label,
            )
        elif question.question_type == "CL" or question.question_type == "RL":
            initial_data = ""
            if incident_workflow is not None:
                answer = (
                    Answer.objects.values_list("answer", flat=True)
                    .filter(question=question, incident_workflow=incident_workflow)
                    .first()
                )
            elif incident is not None:
                answer = (
                    Answer.objects.values_list("answer", flat=True)
                    .filter(
                        question=question,
                        incident_workflow=incident.get_latest_incident_workflow(),
                    )
                    .order_by("-timestamp")
                ).first()
            if answer is not None:
                # initial_data = list(filter(partial(is_not, ""), answer))
                initial_data = list(filter(None, answer.split(",")))

            if question.question_type == "CL":
                choices = countries
            else:
                choices = REGIONAL_AREA
            self.fields[field_name] = forms.MultipleChoiceField(
                choices=choices,
                widget=DropdownCheckboxSelectMultiple(),
                label=question.label,
                initial=initial_data,
            )

    def __init__(self, *args, **kwargs):
        position = -1
        workflow = None
        incident_workflow = None
        incident = None
        if "position" in kwargs:
            position = kwargs.pop("position")
        if "workflow" in kwargs:
            workflow = kwargs.pop("workflow")
        if "incident_workflow" in kwargs:
            incident_workflow = kwargs.pop("incident_workflow")
        if "incident" in kwargs:
            incident = kwargs.pop("incident")
        super().__init__(*args, **kwargs)

        if workflow is not None:
            questions = workflow.questions.all()
        if incident_workflow is not None:
            questions = incident_workflow.workflow.questions.all()
        categories = set()

        for question in questions:
            categories.add(question.category)
        categories = list(categories)
        categories.sort(key=lambda x: x.position)
        category = categories[position]

        subquestion = (
            Question.objects.all()
            .filter(category=category, id__in=questions.values("id"))
            .order_by("position")
        )

        for question in subquestion:
            self.create_question(question, incident_workflow, incident)


# the first question for preliminary notification
class ContactForm(forms.Form):
    company_name = forms.CharField(
        required=True,
        label="Company name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "company_name"}),
    )

    contact_lastname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_lastname"}),
    )
    contact_firstname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_firstname"}),
    )
    contact_title = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_title"}),
    )
    contact_email = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.EmailInput(attrs={"class": "contact_email"}),
    )
    contact_telephone = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_telephone"}),
    )

    is_technical_the_same = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "required checkbox ",
                "onclick": "if (checked==true) {"
                "document.getElementsByClassName('technical_lastname')[0].value="
                "document.getElementsByClassName('contact_lastname')[0].value; "
                "document.getElementsByClassName('technical_firstname')[0].value="
                "document.getElementsByClassName('contact_firstname')[0].value; "
                "document.getElementsByClassName('technical_title')[0].value="
                "document.getElementsByClassName('contact_title')[0].value; "
                "document.getElementsByClassName('technical_email')[0].value="
                "document.getElementsByClassName('contact_email')[0].value; "
                "document.getElementsByClassName('technical_telephone')[0].value="
                "document.getElementsByClassName('contact_telephone')[0].value;}",
            }
        ),
        initial=False,
    )
    technical_lastname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_lastname"}),
    )
    technical_firstname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_firstname"}),
    )
    technical_title = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_title"}),
    )
    technical_email = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.EmailInput(attrs={"class": "technical_email"}),
    )
    technical_telephone = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_telephone"}),
    )

    incident_reference = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "title": _(
                    "To make your incident easier to locate and track, please include a reference "
                    "(e.g., an identifier, internal reference, CERT reference, etc.)."
                ),
                "data-bs-toggle": "tooltip",
            }
        ),
    )
    complaint_reference = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "title": _(
                    "Insert a police report that you have filed with the police"
                ),
                "data-bs-toggle": "tooltip",
            }
        ),
    )

    def prepare_initial_value(**kwargs):
        request = kwargs.pop("request")
        if request.user.is_authenticated:
            return {
                "company_name": get_active_company_from_session(request),
                "contact_lastname": request.user.last_name,
                "contact_firstname": request.user.first_name,
                "contact_email": request.user.email,
                "contact_telephone": request.user.phone_number,
            }
        return {}


# prepare an array of sector and services
def construct_services_array(root_sectors):
    categs = dict()
    services = Service.objects.filter(
        Q(sector__in=root_sectors) | Q(sector__parent__in=root_sectors)
    )

    final_categs = []
    for service in services:
        if not categs.get(service.sector):
            categs[service.sector] = [[service.id, service]]
        else:
            categs[service.sector].append([service.id, service])

    for sector, list_of_options in categs.items():
        name = sector.name
        while sector.parent is not None:
            name = _(sector.parent.name) + " - " + _(name)
            sector = sector.parent
        final_categs.append([name, list_of_options])

    return final_categs


class RegulationForm(forms.Form):
    regulations = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
    )

    def __init__(self, *args, **kwargs):
        regulators = kwargs["initial"].get("regulators", None)
        super().__init__(*args, **kwargs)

        if regulators is not None:
            self.fields["regulations"].choices = construct_regulation_array(
                regulators.all()
            )


# prepare an array of regulations
def construct_regulation_array(regulators):
    regulations_to_select = []
    regulations_id = (
        SectorRegulation.objects.all()
        .filter(regulator__in=regulators)
        .values_list("regulation", flat=True)
    )

    regulations = Regulation.objects.all().filter(id__in=regulations_id)

    for regulation in regulations:
        regulations_to_select.append([regulation.id, regulation.label])

    return regulations_to_select


class RegulatorForm(forms.Form):
    # generic impact definitions
    regulators = forms.MultipleChoiceField(
        required=True,
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
        label="Send notification to:",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields["regulators"].choices = [
                (k.id, k.name + " " + k.full_name) for k in Regulator.objects.all()
            ]
        except Exception:
            self.fields["regulators"].choices = []

    def get_selected_data(self):
        return self.fields["regulators"].initial


# select the detection date
class DetectionDateForm(forms.Form):
    incident_timezone = forms.ChoiceField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False,
        label=gettext_lazy("Select the incident time zone"),
        initial=TIME_ZONE,
    )

    detection_date = forms.DateTimeField(
        required=True,
        widget=DateTimePickerInput(
            options={
                "maxDate": datetime.today().strftime("%Y-%m-%d 23:59"),
            },
        ),
    )


class SectorForm(forms.Form):
    sectors = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
    )

    def __init__(self, *args, **kwargs):
        regulations = kwargs["initial"]["regulations"]
        regulators = kwargs["initial"]["regulators"]
        super().__init__(*args, **kwargs)

        self.fields["sectors"].choices = construct_sectors_array(
            regulations.all(), regulators.all()
        )

        if len(self.fields["sectors"].choices) == 0:
            self.fields["sectors"].required = False


def construct_sectors_array(regulations, regulators):
    sector_regulations = SectorRegulation.objects.filter(
        regulation__in=regulations, regulator__in=regulators
    )
    all_sectors = Sector.objects.filter(sectorregulation__in=sector_regulations)
    categs = dict()

    for sector in all_sectors:
        if sector.parent is not None:
            if not categs.get(sector.parent.name):
                categs[sector.parent.name] = [[sector.id, sector]]
            else:
                categs[sector.parent.name].append([sector.id, sector])
        else:
            if not categs.get(sector.name):
                categs[sector.name] = []
    final_categs = []
    for sector, list_of_options in categs.items():
        final_categs.append([sector, list_of_options])

    return final_categs


def get_forms_list(incident=None, workflow=None, is_regulator=False):
    category_tree = []
    if incident is None:
        category_tree = [
            ContactForm,
            RegulatorForm,
            RegulationForm,
            SectorForm,
            DetectionDateForm,
        ]
    else:
        category_tree.append(IncidenteDateForm)
        impact_needed = False
        if workflow is None:
            workflow = incident.get_next_step()
            if workflow.is_impact_needed:
                impact_needed = True
            categories = set()
            for question in workflow.questions.all():
                categories.add(question.category)
        else:
            if workflow.is_impact_needed:
                impact_needed = True
            categories = set()
            for question in workflow.questions.all():
                categories.add(question.category)
        for _category in categories:
            category_tree.append(QuestionForm)
        if impact_needed:
            category_tree.append(ImpactForm)
        if is_regulator:
            category_tree.append(RegulatorIncidentWorkflowCommentForm)

    return category_tree


class RegulatorIncidentEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = self.instance.id

    class Meta:
        model = Incident
        fields = [
            "id",
            "incident_id",
            "is_significative_impact",
            "review_status",
            "incident_status",
        ]


class RegulatorIncidentWorkflowCommentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = self.instance.id

    class Meta:
        model = IncidentWorkflow
        fields = [
            "id",
            "comment",
        ]


class ImpactForm(forms.Form):
    impacts = forms.MultipleChoiceField(
        required=False,
        widget=ServicesListCheckboxSelectMultiple(initial=None),
    )

    # prepare an array of impacts from incident sectorized
    def construct_impact_array(self, incident):
        impacts_array = []
        regulation = incident.sector_regulation.regulation
        for sector in incident.affected_sectors.all():
            subgroup = []
            if sector.impact_set.filter(regulation=regulation).count() > 0:
                for impact in sector.impact_set.filter(regulation=regulation):
                    subgroup.append([impact.id, impact.label])
                impacts_array.append(
                    [sector.name, sorted(subgroup, key=lambda item: item[1])]
                )

        # Not needed anymore : just keep in case
        # impacts_without_sector = Impact.objects.all().filter(
        #     regulation=incident.sector_regulation.regulation, sectors=None
        # )
        # if impacts_without_sector.count() > 0:
        #     subgroup = []
        #     for impact in impacts_without_sector:
        #         subgroup.append([impact.id, impact.label])
        #     impacts_array.append(['others', subgroup])

        return impacts_array

    def __init__(self, *args, **kwargs):
        incident = None
        incident_workflow = None
        if "incident" in kwargs:
            incident = kwargs.pop("incident")
        if "incident_workflow" in kwargs:
            incident_workflow = kwargs.pop("incident_workflow")
        super().__init__(*args, **kwargs)

        if incident is not None:
            self.fields["impacts"].choices = self.construct_impact_array(incident)
        if incident_workflow is not None:
            # only with ServicesListCheckboxSelectMultiple
            self.fields["impacts"].widget.initial_data = [
                i.id for i in incident_workflow.impacts.all()
            ]
        else:
            previous_incident_workflow = incident.get_latest_incident_workflow()
            if previous_incident_workflow is not None:
                # only with ServicesListCheckboxSelectMultiple
                self.fields["impacts"].widget.initial_data = [
                    i.id for i in previous_incident_workflow.impacts.all()
                ]


# let the user change the date of his incident
class IncidenteDateForm(forms.ModelForm):
    incident_timezone = forms.ChoiceField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False,
        label=gettext_lazy("Select the incident time zone"),
        initial=TIME_ZONE,
    )

    incident_notification_date = forms.DateTimeField(
        widget=DateTimePickerInput(),
        required=False,
    )

    incident_detection_date = forms.DateTimeField(
        widget=DateTimePickerInput(
            options={}, attrs={"class": "incident_detection_date"}
        ),
        required=False,
        help_text=gettext_lazy("Date Format YYYY-MM-DD HH:MM"),
    )

    incident_starting_date = forms.DateTimeField(
        widget=DateTimePickerInput(
            options={}, attrs={"class": "incident_starting_date"}
        ),
        required=False,
        help_text=gettext_lazy("Date Format YYYY-MM-DD HH:MM"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.incident = self.instance

        self.fields["incident_notification_date"].disabled = True

        if self.incident:
            i_timezone = (
                self.incident.incident_timezone
                if self.incident.incident_timezone
                else TIME_ZONE
            )
            i_notification_date = (
                self.incident.incident_notification_date
                if self.incident.incident_notification_date
                else None
            )

            i_detection_date = (
                self.incident.incident_detection_date
                if self.incident.incident_detection_date
                else None
            )
            timezone = pytz.timezone(i_timezone)

            if i_notification_date:
                maxDate_notification = format_datetime_astimezone(
                    i_notification_date, timezone
                )
                self.fields["incident_detection_date"].widget.config.options[
                    "maxDate"
                ] = maxDate_notification

                self.fields["incident_starting_date"].widget.config.options[
                    "maxDate"
                ] = maxDate_notification

            if self.incident.sector_regulation.is_detection_date_needed:
                maxDate_detection = format_datetime_astimezone(
                    i_detection_date, timezone
                )

                self.fields["incident_starting_date"].widget.config.options[
                    "maxDate"
                ] = maxDate_detection
                self.fields["incident_detection_date"].disabled = True
                self.fields["incident_timezone"].disabled = True

            if i_timezone != TIME_ZONE:
                self.fields["incident_timezone"].disabled = True

            set_initial_datetime(
                self,
                "incident_notification_date",
                i_notification_date,
                timezone,
            )

            set_initial_datetime(
                self,
                "incident_detection_date",
                i_detection_date,
                timezone,
            )
            set_initial_datetime(
                self,
                "incident_starting_date",
                self.incident.incident_starting_date,
                timezone,
            )

    class Meta:
        model = Incident
        fields = [
            "id",
            "incident_timezone",
            "incident_notification_date",
            "incident_detection_date",
            "incident_starting_date",
        ]


class IncidentWorkflowForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_status"].required = False
        self.fields["review_status"].widget.attrs = {
            "class": "border-0 form-select-sm py-0 select-break-spaces",
            "onchange": f"onChangeWorkflowStatus(this, {self.instance.incident_id}, {self.instance.pk})",
        }

    class Meta:
        model = IncidentWorkflow
        fields = ["review_status"]


class IncidentStatusForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(IncidentStatusForm, self).clean()
        # prevent is_significative_impact to go FALSE when we change an other field
        if len(cleaned_data) > 1:
            cleaned_data['is_significative_impact'] = self.instance.is_significative_impact
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        onchange_funtion = f"onChangeIncident(this, {self.instance.pk})"
        classes_select_widget = "border-0 form-select-sm py-0 select-break-spaces"

        self.fields["incident_id"].widget.attrs = {
            "class": "form-control-sm",
            "onchange": onchange_funtion,
        }
        self.fields["incident_status"].widget.attrs = {
            "class": classes_select_widget,
            "onchange": onchange_funtion,
        }
        self.fields["review_status"].widget.attrs = {
            "class": classes_select_widget,
            "onchange": onchange_funtion,
        }

        self.fields["is_significative_impact"].widget.attrs = {
            "class": "large-checkbox",
            "onchange": onchange_funtion,
        }

    class Meta:
        model = Incident
        fields = [
            "incident_id",
            "review_status",
            "incident_status",
            "is_significative_impact",
        ]

        required = {
            "incident_id": False,
            "review_status": False,
            "incident_status": False,
            "is_significative_impact": False,
        }


def format_datetime_astimezone(datetime, timezone):
    return datetime.astimezone(timezone).strftime("%Y-%m-%d %H:%M")


def set_initial_datetime(form, field_name, datetime_value, timezone):
    if datetime_value:
        form.initial[field_name] = format_datetime_astimezone(datetime_value, timezone)
