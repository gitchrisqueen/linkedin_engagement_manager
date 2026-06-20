import os
import random
import tempfile
import urllib.request
from datetime import datetime
from typing import Optional, Union

from lxml.etree import tostring
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_xml
from pptx.slide import Slide
from pydantic import BaseModel, Field, HttpUrl, conlist, StrictStr
from pydantic_extra_types.color import Color


# Generic slide model for reusability
class CarouselSlide(BaseModel):
    title: Optional[StrictStr] = Field(None, description="Title or heading of the slide")
    content: Optional[StrictStr] = Field(None, description="Main content of the slide", max_length=500)
    image_url: Optional[HttpUrl] = Field(None, description="URL to an image")
    image_path: Optional[StrictStr] = Field(None, description="Path to an image")


# Specific Carousel Templates

class EducationalContentSlide(CarouselSlide):
    # Custom Educational Content slides could have additional elements if needed
    pass


class EducationalContentCarousel(BaseModel):
    cover: EducationalContentSlide = Field(..., description="Cover Slide: A bold title that clearly states the topic.")
    contents: conlist(EducationalContentSlide, min_length=1, max_length=4) = Field(...,
                                                                                   description="Content Slides: Each slide covers one tip or step with a combination of short text and relevant visuals.")
    call_to_action: EducationalContentSlide = Field(...,
                                                    description="Final Slide: Summarize key points and add a call to action.")


class CaseStudySlide(CarouselSlide):
    # Custom case study slides can have additional constraints or attributes
    pass


class CaseStudyCarousel(BaseModel):
    cover: CaseStudySlide = Field(...,
                                  description="Cover Slide: Title of the case study with the client’s name or project outcome.")
    challenge: CaseStudySlide = Field(..., description="Slide 2: Brief description of the problem faced by the client.")
    solution: CaseStudySlide = Field(..., description="Slide 3: Explanation of the approach or solution.")
    results: CaseStudySlide = Field(..., description="Slide 4: Highlight measurable results with data or visuals.")
    testimonial: Optional[CaseStudySlide] = Field(None,
                                                  description="Slide 5 (Optional): Include a client quote or feedback.")
    call_to_action: CaseStudySlide = Field(...,
                                           description="Final Slide: Encourage viewers to reach out for more information.")


class PersonalStorySlide(CarouselSlide):
    # Custom personal story slide if needed
    pass


class PersonalStoryCarousel(BaseModel):
    cover: PersonalStorySlide = Field(..., description="Cover Slide: Compelling title introducing the personal story.")
    story_slides: conlist(PersonalStorySlide, min_length=1, max_length=3) = Field(...,
                                                                                  description="Slides 2-4: Key moments in the journey.")
    takeaway: PersonalStorySlide = Field(..., description="Slide 5: Summary or lessons learned from the experience.")
    call_to_action: PersonalStorySlide = Field(...,
                                               description="Final Slide: Encourage viewers to share their own stories or connect with you for further discussion.")


class IndustryInsightSlide(CarouselSlide):
    # Custom industry insight slide for trends and insights
    pass


class IndustryInsightsCarousel(BaseModel):
    cover: IndustryInsightSlide = Field(...,
                                        description="Cover Slide: Title with an attention-grabbing phrase for industry insights.")
    insights: conlist(IndustryInsightSlide, min_length=1, max_length=4) = Field(...,
                                                                                description="Slides 2-5: Individual trends or insights with visuals.")
    call_to_action: IndustryInsightSlide = Field(...,
                                                 description="Final Slide: Summary and call-to-action for opinions on the trends.")


class EventRecapSlide(CarouselSlide):
    # Custom event recap slide if additional details are needed
    pass


class EventRecapCarousel(BaseModel):
    cover: EventRecapSlide = Field(..., description="cover Slide: Event title and date.")
    key_moments: conlist(EventRecapSlide, min_length=1, max_length=3) = Field(...,
                                                                              description="Slides 2-4: Key takeaways or highlights from the event.")
    call_to_action: EventRecapSlide = Field(...,
                                            description="Final Slide: Thank attendees and provide a call-to-action for future events or download additional resources.")


class TestimonialSlide(CarouselSlide):
    client_name: str = Field(..., description="Name of the client providing the testimonial")
    client_logo_url: Optional[HttpUrl] = Field(None, description="URL to the client’s logo or photo")


class TestimonialCarousel(BaseModel):
    cover: CarouselSlide = Field(...,
                                 description="Cover Slide: Cover slide with a title like 'What Our Clients Are Saying'.")
    testimonials: conlist(TestimonialSlide, min_length=1, max_length=3) = Field(...,
                                                                                description="Slides 2-4: Individual testimonials with a quote, client name, and photo.")
    call_to_action: CarouselSlide = Field(...,
                                          description="Final Slide: Call-to-action to encourage viewers to reach out for similar results.")


class ProductDemoSlide(CarouselSlide):
    # Custom product demo slide if additional details are needed
    pass


class ProductDemoCarousel(BaseModel):
    cover: ProductDemoSlide = Field(...,
                                    description="Cover Slide: Introduction to the product with a compelling headline.")
    main_feature: ProductDemoSlide = Field(...,
                                           description="Slide 2: Highlight the main feature of the product with an image.")
    additional_features: conlist(ProductDemoSlide, min_length=1, max_length=2) = Field(...,
                                                                                       description="Slides 3-4: Additional features of the product.")
    call_to_action: ProductDemoSlide = Field(...,
                                             description="Final Slide: Call-to-action to learn more or sign up for a demo.")


class PowerPointThemeColors(BaseModel):
    dk1: Optional[Color] = Field(None, description="RGB color code for the 1st dark color in the theme")
    lt1: Optional[Color] = Field(None, description="RGB color code for the 1st light color in the theme")
    dk2: Optional[Color] = Field(None, description="RGB color code for the 2nd dark color in the theme")
    lt2: Optional[Color] = Field(None, description="RGB color code for the 2nd light color in the theme")
    accent1: Optional[Color] = Field(None, description="RGB color code for the 1st accent color in the theme")
    accent2: Optional[Color] = Field(None, description="RGB color code for the 2nd accent color in the theme")
    accent3: Optional[Color] = Field(None, description="RGB color code for the 3rd accent color in the theme")
    accent4: Optional[Color] = Field(None, description="RGB color code for the 4th accent color in the theme")
    accent5: Optional[Color] = Field(None, description="RGB color code for the 5th accent color in the theme")
    accent6: Optional[Color] = Field(None, description="RGB color code for the 6th accent color in the theme")
    hlink: Optional[Color] = Field(None, description="RGB color code for the hyperlink color in the theme")
    folHlink: Optional[Color] = Field(None,
                                      description="RGB color code for the followed hyperlink color in the theme")


def create_ppt(ppt_name, carousel_data: Union[
    EducationalContentCarousel,
    CaseStudyCarousel,
    PersonalStoryCarousel,
    IndustryInsightsCarousel,
    EventRecapCarousel,
    TestimonialCarousel,
    ProductDemoCarousel],
               my_theme: PowerPointThemeColors = PowerPointThemeColors(**{"lt1": "e9d437", "dk2": "a89816"}),
               design_number: int = 1):
    current_dir = os.path.dirname(__file__)
    generated_dir = os.path.join(current_dir, "generated_designs")
    os.makedirs(generated_dir, exist_ok=True)
    design_path = os.path.join(current_dir, f"carousel_designs/Design-{design_number}.pptx")
    prs = Presentation(design_path)

    if isinstance(carousel_data, EducationalContentCarousel):
        # Handle EducationalContentCarousel
        prs = create_ppt_educational_content_carousel(prs, carousel_data)
        pass
    elif isinstance(carousel_data, CaseStudyCarousel):
        # Handle CaseStudyCarousel
        prs = create_ppt_case_study_carousel(prs, carousel_data)
        pass
    elif isinstance(carousel_data, PersonalStoryCarousel):
        prs = create_ppt_personal_story_carousel(prs, carousel_data)
    elif isinstance(carousel_data, IndustryInsightsCarousel):
        prs = create_ppt_industry_insights_carousel(prs, carousel_data)
    elif isinstance(carousel_data, EventRecapCarousel):
        prs = create_ppt_event_recap_carousel(prs, carousel_data)
    elif isinstance(carousel_data, TestimonialCarousel):
        prs = create_ppt_testimonial_carousel(prs, carousel_data)
    elif isinstance(carousel_data, ProductDemoCarousel):
        prs = create_ppt_product_demo_carousel(prs, carousel_data)

    file_path = os.path.join(generated_dir, f"{ppt_name}.pptx")
    prs.save(file_path)

    convert_ppt_theme_colors(file_path, my_theme)

    return f"{file_path}"


def get_default_image_path() -> str:
    # Get the default image path local to this file
    file_dir = os.path.dirname(__file__)
    default_image_path = os.path.join(file_dir, "images/image.png")
    return default_image_path


def get_pexels_image_path(query: str, default_path: str) -> str:
    """Download a Pexels image matching *query* to a temp file and return its path.

    Falls back to *default_path* when PEXELS_API_KEY is absent or the request
    fails so that carousel creation never hard-crashes on a network error.
    """
    try:
        from cqc_lem.utilities.pexels_helper import get_photo
        photo = get_photo(query)
        url = photo.medium  # medium-size JPEG is a good balance for slides
        suffix = ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        urllib.request.urlretrieve(url, tmp.name)
        return tmp.name
    except Exception:
        return default_path


def create_ppt_educational_content_carousel(prs: Presentation, carousel: EducationalContentCarousel) -> Presentation:
    """
    Create a PowerPoint presentation for Educational Content Carousel.

    Parameters:
    - prs: Presentation object to add slides to.
    - carousel: EducationalContentCarousel containing carouseldata.

    """

    # Get the default image path local to this file
    default_image_path = get_default_image_path()

    # Slide 1: Cover
    cover_layouts = [create_title_layout_slide, create_title_only_layout_slide,
                     create_title_and_body_layout_slide]
    cover_slide_args = {
        "prs": prs,
        "title": carousel.cover.title,
        "subtitle": carousel.cover.content,
        "body_text": carousel.cover.content
    }
    cover_slide = random.choice(cover_layouts)(
        **cover_slide_args
    )

    # Slide 2-5: Content/Tips
    content_layouts = [create_title_and_body_layout_slide, create_one_column_text_layout_slide,
                       # create_ppt_for_title_and_two_columns_layout # TODO: Figure out if and how to implement this one
                       ]

    content_slide_args = {
        "prs": prs
    }
    for content in carousel.contents:
        content_slide_args["title"] = content.title
        content_slide_args["body_text"] = content.content
        image_path = getattr(content, "image_path", None)
        content_slide_args["image_path"] = image_path or get_pexels_image_path(
            content.title or "professional", default_image_path
        )
        content_slide = random.choice(content_layouts)(
            **content_slide_args
        )

    # Slide 6: Conclusion
    conclusion_layouts = [create_section_title_and_description_layout_slide, create_custom_3_1_layout_slide,
                          create_caption_only_layout_slide]
    cta_image_path = getattr(carousel.call_to_action, "image_path", None) or get_pexels_image_path(
        carousel.call_to_action.title or "success", default_image_path
    )
    conclusion_slide_args = {
        "prs": prs,
        "title": carousel.call_to_action.title,
        "description": carousel.call_to_action.content,
        "subtitle": carousel.call_to_action.content,
        "image_path": cta_image_path,
    }
    conclusion_slide = random.choice(conclusion_layouts)(
        **conclusion_slide_args
    )

    return prs  # Return the presentation for further modifications or saving


def create_ppt_case_study_carousel(prs: Presentation, case_study_carousel: CaseStudyCarousel) -> Presentation:
    """
    Create a PowerPoint presentation for Case Study Carousel.

    Parameters:
    - prs: Presentation object to add slides to.
    - case_study_carousel: CaseStudyCarousel instance with structured content for each slide.
    """

    # Slide 1: Cover
    cover_layouts = [create_title_layout_slide, create_section_header_layout_slide, create_title_only_layout_slide]
    cover_kwargs = {
        'prs': prs,
        'percentage': getattr(case_study_carousel.cover, 'percentage', ''),
        'title': case_study_carousel.cover.title,
        'subtitle': getattr(case_study_carousel.cover, 'subtitle', case_study_carousel.cover.content)
    }
    cover_slide = random.choice(cover_layouts)(**cover_kwargs)

    # Slide 2: Challenge
    challenge_layouts = [create_title_and_body_layout_slide, create_one_column_text_layout_slide]
    challenge_kwargs = {
        'prs': prs,
        'title': case_study_carousel.challenge.title,
        'body_text': case_study_carousel.challenge.content,
        'image_path': getattr(case_study_carousel.challenge, 'image_path', None) or get_pexels_image_path(
            case_study_carousel.challenge.title or "challenge", get_default_image_path()
        ),
    }
    challenge_slide = random.choice(challenge_layouts)(**challenge_kwargs)

    # Slide 3: Solution
    solution_layouts = [create_title_and_body_layout_slide, create_title_and_body_1_layout_slide,
                        # create_title_and_two_columns_layout_slide # TODO: Figure how to implement this one
                        ]
    solution_kwargs = {
        'prs': prs,
        'title': case_study_carousel.solution.title,
        'body_text': case_study_carousel.solution.content
    }
    solution_slide = random.choice(solution_layouts)(**solution_kwargs)

    # Slide 4: Results
    results_layouts = [create_big_number_layout_slide, create_title_and_body_layout_slide,
                       create_one_column_text_layout_slide]
    results_kwargs = {
        'prs': prs,
        'title': case_study_carousel.results.title,
        'body_text': case_study_carousel.results.content,
        'image_path': getattr(case_study_carousel.results, 'image_path', None) or get_pexels_image_path(
            case_study_carousel.results.title or "results", get_default_image_path()
        ),
        'big_number': getattr(case_study_carousel.results, 'big_number', ''),
        'subtitle': getattr(case_study_carousel.results, 'subtitle', case_study_carousel.results.content),
    }
    results_slide = random.choice(results_layouts)(**results_kwargs)

    # Slide 5: Testimonial
    testimonial_layouts = [create_caption_only_layout_slide, create_blank_1_1_layout_slide]
    testimonial_kwargs = {
        'prs': prs,
        'image_path': getattr(case_study_carousel.testimonial, 'image_path', get_default_image_path()),
        'title': getattr(case_study_carousel.testimonial, 'title', "Testimonial"),
        'quote': getattr(case_study_carousel.testimonial, 'quote', case_study_carousel.testimonial.content),
        'author': getattr(case_study_carousel.testimonial, 'author',
                          getattr(case_study_carousel.testimonial, 'title', "Happy Client"))
    }
    testimonial_slide = random.choice(testimonial_layouts)(**testimonial_kwargs)

    # Slide 6: Call to Action
    cta_layouts = [create_section_title_and_description_layout_slide, create_custom_3_1_layout_slide]
    cta_kwargs = {
        'prs': prs,
        'title': case_study_carousel.call_to_action.title,
        'subtitle': case_study_carousel.call_to_action.content,
        'description': case_study_carousel.call_to_action.content
    }
    cta_slide = random.choice(cta_layouts)(**cta_kwargs)

    return prs  # Return the presentation for further modifications or saving


def create_ppt_personal_story_carousel(prs: Presentation, carousel: PersonalStoryCarousel) -> Presentation:
    default_image = get_default_image_path()

    cover_layouts = [create_title_layout_slide, create_section_header_layout_slide, create_title_only_layout_slide]
    random.choice(cover_layouts)(
        prs=prs, title=carousel.cover.title, subtitle=carousel.cover.content,
        percentage="", body_text=carousel.cover.content
    )

    story_layouts = [create_title_and_body_layout_slide, create_one_column_text_layout_slide]
    for slide_data in carousel.story_slides:
        random.choice(story_layouts)(
            prs=prs, title=slide_data.title, body_text=slide_data.content,
            image_path=getattr(slide_data, "image_path", None) or get_pexels_image_path(
                slide_data.title or "story", default_image
            ),
        )

    create_title_and_body_1_layout_slide(
        prs=prs, title=carousel.takeaway.title, body_text=carousel.takeaway.content
    )

    cta_layouts = [create_section_title_and_description_layout_slide, create_custom_3_1_layout_slide]
    random.choice(cta_layouts)(
        prs=prs, title=carousel.call_to_action.title,
        description=carousel.call_to_action.content, subtitle=carousel.call_to_action.content
    )
    return prs


def create_ppt_industry_insights_carousel(prs: Presentation, carousel: IndustryInsightsCarousel) -> Presentation:
    default_image = get_default_image_path()

    cover_layouts = [create_title_layout_slide, create_title_only_layout_slide]
    random.choice(cover_layouts)(
        prs=prs, title=carousel.cover.title, subtitle=carousel.cover.content
    )

    insight_layouts = [create_title_and_body_layout_slide, create_one_column_text_layout_slide]
    for insight in carousel.insights:
        random.choice(insight_layouts)(
            prs=prs, title=insight.title, body_text=insight.content,
            image_path=getattr(insight, "image_path", None) or get_pexels_image_path(
                insight.title or "industry", default_image
            ),
        )

    cta_layouts = [create_section_title_and_description_layout_slide, create_custom_3_1_layout_slide]
    random.choice(cta_layouts)(
        prs=prs, title=carousel.call_to_action.title,
        description=carousel.call_to_action.content, subtitle=carousel.call_to_action.content
    )
    return prs


def create_ppt_event_recap_carousel(prs: Presentation, carousel: EventRecapCarousel) -> Presentation:
    default_image = get_default_image_path()

    cover_layouts = [create_title_layout_slide, create_section_header_layout_slide]
    random.choice(cover_layouts)(
        prs=prs, title=carousel.cover.title, subtitle=carousel.cover.content,
        percentage=""
    )

    moment_layouts = [create_title_and_body_layout_slide, create_one_column_text_layout_slide]
    for moment in carousel.key_moments:
        random.choice(moment_layouts)(
            prs=prs, title=moment.title, body_text=moment.content,
            image_path=getattr(moment, "image_path", None) or get_pexels_image_path(
                moment.title or "event", default_image
            ),
        )

    cta_layouts = [create_section_title_and_description_layout_slide, create_custom_3_1_layout_slide]
    random.choice(cta_layouts)(
        prs=prs, title=carousel.call_to_action.title,
        description=carousel.call_to_action.content, subtitle=carousel.call_to_action.content
    )
    return prs


def create_ppt_testimonial_carousel(prs: Presentation, carousel: TestimonialCarousel) -> Presentation:
    cover_layouts = [create_title_layout_slide, create_title_only_layout_slide]
    random.choice(cover_layouts)(
        prs=prs, title=carousel.cover.title, subtitle=carousel.cover.content
    )

    for testimonial in carousel.testimonials:
        create_blank_1_1_layout_slide(
            prs=prs,
            quote=f'"{testimonial.content}"',
            author=f"— {testimonial.client_name}"
        )

    cta_layouts = [create_section_title_and_description_layout_slide, create_custom_3_1_layout_slide]
    random.choice(cta_layouts)(
        prs=prs, title=carousel.call_to_action.title,
        description=carousel.call_to_action.content, subtitle=carousel.call_to_action.content
    )
    return prs


def create_ppt_product_demo_carousel(prs: Presentation, carousel: ProductDemoCarousel) -> Presentation:
    default_image = get_default_image_path()

    cover_layouts = [create_title_layout_slide, create_title_only_layout_slide]
    random.choice(cover_layouts)(
        prs=prs, title=carousel.cover.title, subtitle=carousel.cover.content
    )

    feature_layouts = [create_title_and_body_layout_slide, create_one_column_text_layout_slide]
    random.choice(feature_layouts)(
        prs=prs, title=carousel.main_feature.title, body_text=carousel.main_feature.content,
        image_path=getattr(carousel.main_feature, "image_path", None) or get_pexels_image_path(
            carousel.main_feature.title or "product", default_image
        ),
    )

    for feature in carousel.additional_features:
        random.choice(feature_layouts)(
            prs=prs, title=feature.title, body_text=feature.content,
            image_path=getattr(feature, "image_path", None) or get_pexels_image_path(
                feature.title or "feature", default_image
            ),
        )

    cta_layouts = [create_section_title_and_description_layout_slide, create_custom_3_1_layout_slide]
    random.choice(cta_layouts)(
        prs=prs, title=carousel.call_to_action.title,
        description=carousel.call_to_action.content, subtitle=carousel.call_to_action.content
    )
    return prs


def debug_slide(slide):
    for shape in slide.shapes:
        print(f"Shape: {shape.name}, Type: {shape.shape_type}, Placeholder: {shape.placeholder_format.idx}")


def convert_ppt_theme_colors(ppt_path, theme_colors: PowerPointThemeColors):
    # Load the presentation
    prs = Presentation(ppt_path)

    # Get the Slide Master
    slide_master = prs.slide_master
    slide_master_part = slide_master.part

    # Get the Theme and part
    theme_part = slide_master_part.part_related_by(RT.THEME)
    theme = parse_xml(theme_part.blob)  # theme here is an <a:theme> element

    # For each of the attributes in the PowerPointThemeColors model, find the corresponding XML element and update the color value
    for field_name, field_value in theme_colors:
        if field_value:
            color_element = theme.xpath(f'a:themeElements/a:clrScheme/a:{field_name}/a:srgbClr')[0]
            # print(f"{field_name} color before: {color_element.get('val')}")
            set_color = field_value.as_hex(format="long").replace("#", "")
            # print(f"{field_name} color after: {set_color}")
            color_element.set('val', set_color.encode('utf-8'))

    # Serialize the modified XML back to the theme part
    theme_part._blob = tostring(theme)

    # print(f"Blob After: {theme_part.blob}")

    # Save the presentation
    prs.save(ppt_path)


def set_ppt_theme_colors(ppt_path, theme_colors: dict = None):
    # Load default theme colors
    if theme_colors is None:
        theme_colors = {
            "dk1": "ffffff",
            "lt1": "ffffff",
            "dk2": "ffffff",
            "lt2": "ffffff",
            "accent1": "ffffff",
            "accent2": "ffffff",
            "accent3": "ffffff",
            "accent4": "ffffff",
            "accent5": "ffffff",
            "accent6": "ffffff",
            "hlink": "ffffff",
            "folHlink": "ffffff"
        }

    # Load the presentation
    prs = Presentation(ppt_path)

    # Get the Slide Master
    slide_master = prs.slide_master
    slide_master_part = slide_master.part

    # Get the Theme and part
    theme_part = slide_master_part.part_related_by(RT.THEME)
    theme = parse_xml(theme_part.blob)  # theme here is an <a:theme> element

    # For each of the theme color names in the themes dict, find the corresponding XML element and update the color value
    for theme_color_name, theme_color_hex_value in theme_colors.items():
        if theme_color_name:
            color_element = theme.xpath(f'a:themeElements/a:clrScheme/a:{theme_color_name}/a:srgbClr')[0]
            # print(f"{theme_color_name} color before: {color_element.get('val')}")
            color_element.set('val', theme_color_hex_value.encode('utf-8'))
            # print(f"{theme_color_name} color after: {theme_color_hex_value}")

    # Serialize the modified XML back to the theme part
    theme_part._blob = tostring(theme)

    # Save the presentation
    prs.save(ppt_path)


def get_attr_gracefully(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception as e:
        print(f"Error accessing attribute ({attr}): {e}")
    return None


def create_title_layout_slide(prs: Presentation, title: str, subtitle: str, **kwargs) -> Slide:
    """Create a PowerPoint slide with the TITLE layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text.
    - subtitle: Additional descriptive text.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.
    """

    # Get the layout and add a slide
    layout = prs.slide_layouts[0]  # Assuming 0 index is the TITLE layout
    slide = prs.slides.add_slide(layout)

    # Populate title and subtitle placeholders
    title_placeholder = slide.shapes.title
    subtitle_placeholder = slide.placeholders[1]  # Assuming index 1 is for subtitle

    # Set the text content
    title_placeholder.text = title
    subtitle_placeholder.text = subtitle

    return slide


def create_section_header_layout_slide(prs: Presentation, percentage: str, title: str, subtitle: str,
                                       **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the SECTION_HEADER layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - percentage: The main percentage or metric to highlight.
    - title: The main title text.
    - subtitle: Additional descriptive text.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[1]  # Assuming 1 index is the SECTION_HEADER layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    percentage_placeholder = slide.placeholders[0]
    title_placeholder = slide.placeholders[1]
    subtitle_placeholder = slide.placeholders[2]

    # Set the text content
    percentage_placeholder.text = percentage
    title_placeholder.text = title
    subtitle_placeholder.text = subtitle

    return slide


def debug_master_slide_placeholders_and_text(design_number: int = 1):
    current_dir = os.path.dirname(__file__)
    design_path = os.path.join(current_dir, f"carousel_designs/Design-{design_number}.pptx")
    prs = Presentation(design_path)
    slide_master = prs.slide_master
    for slide_layout in slide_master.slide_layouts:
        print(f"Slide Layout: {slide_layout.name}")
        for placeholder in slide_layout.placeholders:
            print(f"Placeholder: {placeholder.name}, Type: {placeholder.placeholder_format.idx}")
            for shape in slide_layout.shapes:
                if shape.is_placeholder:
                    phf = shape.placeholder_format
                    print(f"Shape: {shape.name}, Type: {shape.shape_type}, Placeholder: {phf.idx}")
                    if phf.idx == placeholder.placeholder_format.idx:
                        print(f"Text: {shape.text}")
        print("----")


def create_title_and_body_layout_slide(prs: Presentation, title: str, body_text: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the TITLE_AND_BODY layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - body_text: The body text content, which could include bullet points or paragraphs.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[2]  # Assuming 2 index is the TITLE_AND_BODY layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    title_placeholder = slide.placeholders[0]
    body_placeholder = slide.placeholders[1]

    # Set the text content
    title_placeholder.text = title
    body_placeholder.text = body_text

    return slide


def create_title_and_two_columns_layout_slide(prs: Presentation, title: str,
                                              left_column_title: str, left_column_subtitle: str,
                                              right_column_title: str, right_column_subtitle: str,
                                              **kwargs
                                              ) -> Slide:
    """
    Create a PowerPoint slide with the TITLE_AND_TWO_COLUMNS layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - left_column_title: Title for the left column.
    - left_column_subtitle: Subtitle text for the left column.
    - right_column_title: Title for the right column.
    - right_column_subtitle: Subtitle text for the right column.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[3]  # Assuming 3 index is the TITLE_AND_TWO_COLUMNS layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    title_placeholder = slide.placeholders[0]
    left_column_title_placeholder = slide.placeholders[1]
    left_column_subtitle_placeholder = slide.placeholders[2]
    right_column_title_placeholder = slide.placeholders[3]
    right_column_subtitle_placeholder = slide.placeholders[4]

    # Set the text content
    title_placeholder.text = title
    left_column_title_placeholder.text = left_column_title
    left_column_subtitle_placeholder.text = left_column_subtitle
    right_column_title_placeholder.text = right_column_title
    right_column_subtitle_placeholder.text = right_column_subtitle

    return slide


def create_title_only_layout_slide(prs: Presentation, title: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the TITLE_ONLY layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[4]  # Assuming 4 index is the TITLE_ONLY layout
    slide = prs.slides.add_slide(layout)

    # Populate the title placeholder
    title_placeholder = slide.placeholders[0]
    title_placeholder.text = title

    # Return the slide object for further customization
    return slide


def create_main_point_layout_slide(prs: Presentation, title: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the MAIN_POINT layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide, typically a key point or highlight.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[6]  # Assuming 6 index is the MAIN_POINT layout
    slide = prs.slides.add_slide(layout)

    # Populate the title placeholder
    title_placeholder = slide.placeholders[0]
    title_placeholder.text = title

    # Return the slide object for further customization
    return slide


def create_one_column_text_layout_slide(prs: Presentation, title: str, body_text: str, image_path: str = None,
                                        **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the ONE_COLUMN_TEXT layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - body_text: The body text content for the left column.
    - image_path (optional): Path to the image file to be inserted into the picture placeholder.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[5]  # Assuming 5 index is the ONE_COLUMN_TEXT layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    title_placeholder = slide.placeholders[0]
    body_placeholder = slide.placeholders[1]
    picture_placeholder = slide.placeholders[2]

    # Set the text content
    title_placeholder.text = title
    body_placeholder.text = body_text

    # Insert the image if the path is provided
    if image_path:
        picture_placeholder.insert_picture(image_path)

    # Return the slide object for further customization
    return slide


def create_section_title_and_description_layout_slide(prs: Presentation, title: str, description: str,
                                                      **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the SECTION_TITLE_AND_DESCRIPTION layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - description: Subtitle or description text for additional context.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[7]  # Assuming 7 index is the SECTION_TITLE_AND_DESCRIPTION layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    title_placeholder = slide.placeholders[0]
    description_placeholder = slide.placeholders[1]

    # Set the text content
    title_placeholder.text = title
    description_placeholder.text = description

    # Return the slide object for further customization
    return slide


def create_caption_only_layout_slide(prs: Presentation, title: str, image_path: str = None, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the CAPTION_ONLY layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The caption or title text for the slide.
    - image_path: Path to the image file to be inserted into the picture placeholder.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[8]  # Assuming 8 index is the CAPTION_ONLY layout
    slide = prs.slides.add_slide(layout)

    # Populate the title placeholder
    title_placeholder = slide.placeholders[0]
    title_placeholder.text = title

    # Insert the image if the path is provided
    picture_placeholder = slide.placeholders[2]
    if image_path:
        picture_placeholder.insert_picture(image_path)

    # Return the slide object for further customization
    return slide


def create_big_number_layout_slide(prs: Presentation, big_number: str, subtitle: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the BIG_NUMBER layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - big_number: The main number or percentage to highlight on the slide.
    - subtitle: Subtitle text for additional context or explanation.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[9]  # Assuming 9 index is the BIG_NUMBER layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    big_number_placeholder = slide.placeholders[0]
    subtitle_placeholder = slide.placeholders[1]

    # Set the text content
    big_number_placeholder.text = big_number
    subtitle_placeholder.text = subtitle

    # Return the slide object for further customization
    return slide


def create_blank_layout_slide(prs: Presentation, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the BLANK layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing complete customization.
    """
    # Get the layout and add a blank slide
    layout = prs.slide_layouts[10]  # Assuming 10 index is the BLANK layout
    slide = prs.slides.add_slide(layout)

    # Return the slide object for full customization
    return slide


def create_custom_6_1_layout_slide(prs: Presentation, title: str, columns: list[dict], **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the CUSTOM_6_1 (Title and Three Columns) layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - columns: A list of dictionaries, each containing 'metric', 'sub_title', and 'description' for each column.
               Example format: [{'metric': 'XX%', 'sub_title': 'Column 1 Title', 'description': 'Details for Column 1'}, ...]
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[11]  # Assuming 11 index is the CUSTOM_6_1 layout
    slide = prs.slides.add_slide(layout)

    # Set the main title
    title_placeholder = slide.placeholders[0]
    title_placeholder.text = title

    # Populate each column's placeholders
    for i, column_content in enumerate(columns):
        if i > 2:
            break  # Only three columns available

        metric_placeholder = slide.placeholders[3 + i * 3]
        sub_title_placeholder = slide.placeholders[4 + i * 3]
        description_placeholder = slide.placeholders[5 + i * 3]

        # Set content for each column
        metric_placeholder.text = column_content['metric']
        sub_title_placeholder.text = column_content['sub_title']
        description_placeholder.text = column_content['description']

    # Return the slide object for further customization
    return slide


def create_title_only_1_1_layout_slide(prs: Presentation, title: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the TITLE_ONLY_1_1 layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[12]  # Assuming 12 index is the TITLE_ONLY_1_1 layout
    slide = prs.slides.add_slide(layout)

    # Populate the title placeholder
    title_placeholder = slide.placeholders[0]
    title_placeholder.text = title

    # Return the slide object for further customization
    return slide


def create_one_column_text_1_layout_slide(prs: Presentation, title: str, body_text: str, image_path: str = None,
                                          **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the ONE_COLUMN_TEXT_1 layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - body_text: The body text content for the right column.
    - image_path: Path to the image file to be inserted into the picture placeholder.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[13]  # Assuming 13 index is the ONE_COLUMN_TEXT_1 layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    title_placeholder = slide.placeholders[0]
    picture_placeholder = slide.placeholders[1]
    body_placeholder = slide.placeholders[2]

    # Set the text content
    title_placeholder.text = title
    body_placeholder.text = body_text

    # Insert the image if the path is provided
    if image_path:
        picture_placeholder.insert_picture(image_path)

    # Return the slide object for further customization
    return slide


def create_blank_1_1_layout_slide(prs: Presentation, quote: str, author: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the BLANK_1_1 (Quote) layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - quote: The main quote or message for the slide.
    - author: The author or source of the quote.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[14]  # Assuming 14 index is the BLANK_1_1 layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    quote_placeholder = slide.placeholders[0]
    author_placeholder = slide.placeholders[1]

    # Set the text content
    quote_placeholder.text = quote
    author_placeholder.text = author

    # Return the slide object for further customization
    return slide


def create_title_and_two_columns_1_layout_slide(prs: Presentation, title: str, column_1: dict,
                                                column_2: dict, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the TITLE_AND_TWO_COLUMNS_1 layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - column_1: A dictionary with 'sub_title' and 'text' for the left column.
               Example format: {'sub_title': 'Column 1 Title', 'text': 'Content for Column 1'}
    - column_2: A dictionary with 'sub_title' and 'text' for the right column.
               Example format: {'sub_title': 'Column 2 Title', 'text': 'Content for Column 2'}
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[15]  # Assuming 15 index is the TITLE_AND_TWO_COLUMNS_1 layout
    slide = prs.slides.add_slide(layout)

    # Set the main title
    title_placeholder = slide.placeholders[0]
    title_placeholder.text = title

    # Populate left column's placeholders
    column_1_subtitle_placeholder = slide.placeholders[1]
    column_1_text_placeholder = slide.placeholders[2]
    column_1_subtitle_placeholder.text = column_1['sub_title']
    column_1_text_placeholder.text = column_1['text']

    # Populate right column's placeholders
    column_2_subtitle_placeholder = slide.placeholders[3]
    column_2_text_placeholder = slide.placeholders[4]
    column_2_subtitle_placeholder.text = column_2['sub_title']
    column_2_text_placeholder.text = column_2['text']

    # Return the slide object for further customization
    return slide


def create_title_and_body_1_layout_slide(prs: Presentation, title: str, body_text: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the TITLE_AND_BODY_1 layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide.
    - body_text: The body text content for the slide, supporting paragraphs or bullet points.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[16]  # Assuming 16 index is the TITLE_AND_BODY_1 layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    title_placeholder = slide.placeholders[0]
    body_placeholder = slide.placeholders[1]

    # Set the text content
    title_placeholder.text = title
    body_placeholder.text = body_text

    # Return the slide object for further customization
    return slide


def create_custom_3_1_layout_slide(prs: Presentation, title: str, subtitle: str, **kwargs) -> Slide:
    """
    Create a PowerPoint slide with the CUSTOM_3_1 (Thanks) layout.

    Parameters:
    - prs: Presentation object to add slides to.
    - title: The main title text for the slide, typically a closing or thank-you message.
    - subtitle: Additional information or call-to-action text.
    - **kwargs: Additional keyword arguments are thrown away to allow for flexible function calls.

    Returns:
    - Slide: The PowerPoint slide object, allowing further customization.
    """
    # Get the layout and add a slide
    layout = prs.slide_layouts[17]  # Assuming 17 index is the CUSTOM_3_1 (Thanks) layout
    slide = prs.slides.add_slide(layout)

    # Populate the placeholders
    title_placeholder = slide.placeholders[0]
    subtitle_placeholder = slide.placeholders[1]

    # Set the text content
    title_placeholder.text = title
    subtitle_placeholder.text = subtitle

    # Return the slide object for further customization
    return slide


def test_create_educational_ppt():
    """
    Test function to create an EducationalContentCarousel presentation and test the create_ppt function.
    """
    # Sample data for an educational content carousel
    carousel_data = {
        "cover": {
            "title": "5 Tips for Boosting Productivity",
            "content": "Practical ways to get more done every day"
        },
        "contents": [
            {"title": "Tip 1", "content": "Set clear goals for each day."},
            {"title": "Tip 2", "content": "Take regular breaks to recharge."},
            {"title": "Tip 3", "content": "Eliminate distractions to stay focused."},
            {"title": "Tip 4", "content": "Use productivity tools to track your progress."}
        ],
        "call_to_action": {
            "title": "Comment Below",
            "content": "Which Tip Will You Try First?"
        }
    }

    # PPT Name with tiemstamp suffix
    ppt_name = f"Educational_Carousel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    my_ppt = create_ppt(ppt_name, EducationalContentCarousel(**carousel_data))
    print(f"Presentation created: {my_ppt}")


def test_create_case_study_ppt():
    """
    Test function to create an CaseStudyCarousel presentation and test the create_ppt function.
    """
    # Sample data for an case study content carousel
    carousel_data = {
        "cover": {
            "title": "Case Study: Successful Project",
            "content": "An in-depth look at our successful project with Client X"
        },
        "challenge": {
            "title": "The Challenge",
            "content": "Client X faced significant challenges in their market due to increased competition and changing customer preferences.",
            "image_path": get_default_image_path()
        },
        "solution": {
            "title": "Our Solution",
            "content": "We implemented a comprehensive strategy that included market analysis, customer engagement, and product innovation."
        },
        "results": {
            "title": "The Results",
            "content": "Our solution led to a 30% increase in market share and a 20% increase in customer satisfaction.",
            "image_path": get_default_image_path(),
            "big_number": "30%",
            "subtitle": "Increase in Market Share"
        },
        "testimonial": {
            "title": "Client Testimonial",
            "content": "Working with this team was a game-changer for our business. Their expertise and dedication were evident in every step of the process.",
            "image_path": get_default_image_path(),
            "quote": "This team transformed our business.",
            "author": "Jane Doe, CEO of Client X"
        },
        "call_to_action": {
            "title": "Get in Touch",
            "content": "Contact us to learn how we can help your business achieve similar results."
        }
    }

    # PPT Name with timestamp suffix
    ppt_name = f"Case_Study_Carousel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    my_ppt = create_ppt(ppt_name, CaseStudyCarousel(**carousel_data))
    print(f"Presentation created: {my_ppt}")


def test_caption_only_slide(design_number: int = 1):
    current_dir = os.path.dirname(__file__)
    generated_dir = os.path.join(current_dir, "generated_designs")
    os.makedirs(generated_dir, exist_ok=True)
    design_path = os.path.join(current_dir, f"carousel_designs/Design-{design_number}.pptx")
    prs = Presentation(design_path)
    create_caption_only_layout_slide(prs, "Caption Only Slide", image_path=get_default_image_path())
    ppt_name = f"Caption Only Slide_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    file_path = os.path.join(generated_dir, f"{ppt_name}.pptx")
    prs.save(file_path)

    print(f"Created: {file_path}")


def create_carousel_slide_images(
    carousel_data: Union[
        EducationalContentCarousel,
        CaseStudyCarousel,
        PersonalStoryCarousel,
        IndustryInsightsCarousel,
        EventRecapCarousel,
        TestimonialCarousel,
        ProductDemoCarousel,
    ],
    post_id: int,
    output_dir: Optional[str] = None,
    bg_color: tuple = (26, 86, 219),        # default: brand blue
    accent_color: tuple = (255, 255, 255),  # default: white text
    secondary_bg: tuple = (15, 52, 142),    # default: darker blue strip
) -> list[str]:
    """Render carousel slides as 1080x1080 PNG images using Pillow.

    Creates one image per slide in output_dir (defaults to
    assets/images/carousel/{post_id}/). Returns a list of absolute image paths.
    Images are uploaded to LinkedIn directly — no PPTX conversion needed.
    """
    from PIL import Image, ImageDraw, ImageFont

    SLIDE_SIZE = (1080, 1080)
    PADDING = 60
    TITLE_Y = 140
    BODY_Y = 380
    STRIP_H = 80

    if output_dir is None:
        current_dir = os.path.dirname(__file__)
        assets_root = os.path.join(current_dir, "..", "assets", "images", "carousel", str(post_id))
        output_dir = os.path.realpath(assets_root)
    os.makedirs(output_dir, exist_ok=True)

    def _load_font(size: int):
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
        ]
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _load_body_font(size: int):
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    title_font = _load_font(56)
    body_font = _load_body_font(36)
    label_font = _load_font(24)

    def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _render_slide(
        slide_number: int,
        total_slides: int,
        title: str,
        body: str,
        bg_image_path: Optional[str] = None,
    ) -> str:
        img = Image.new("RGB", SLIDE_SIZE, color=bg_color)
        draw = ImageDraw.Draw(img)

        # Optional background image with overlay
        if bg_image_path and os.path.exists(bg_image_path):
            try:
                bg_img = Image.open(bg_image_path).convert("RGB").resize(SLIDE_SIZE)
                overlay = Image.new("RGBA", SLIDE_SIZE, (*bg_color, 200))
                img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")
                draw = ImageDraw.Draw(img)
            except Exception:
                pass  # fall back to solid bg_color

        # Top strip with slide counter
        draw.rectangle([(0, 0), (SLIDE_SIZE[0], STRIP_H)], fill=secondary_bg)
        label = f"{slide_number} / {total_slides}"
        draw.text((PADDING, 22), label, font=label_font, fill=accent_color)

        # Bottom strip / brand bar
        draw.rectangle([(0, SLIDE_SIZE[1] - STRIP_H), (SLIDE_SIZE[0], SLIDE_SIZE[1])], fill=secondary_bg)

        # Title
        title_str = (title or "").strip()
        title_lines = _wrap_text(title_str, title_font, SLIDE_SIZE[0] - PADDING * 2, draw)
        y = TITLE_Y
        for line in title_lines[:4]:
            draw.text((PADDING, y), line, font=title_font, fill=accent_color)
            bbox = draw.textbbox((0, 0), line, font=title_font)
            y += (bbox[3] - bbox[1]) + 12

        # Divider
        draw.rectangle([(PADDING, y + 16), (SLIDE_SIZE[0] - PADDING, y + 20)], fill=(*accent_color, 120))

        # Body text
        body_str = (body or "").strip()
        body_lines = _wrap_text(body_str, body_font, SLIDE_SIZE[0] - PADDING * 2, draw)
        y = max(y + 40, BODY_Y)
        for line in body_lines[:8]:
            draw.text((PADDING, y), line, font=body_font, fill=accent_color)
            bbox = draw.textbbox((0, 0), line, font=body_font)
            y += (bbox[3] - bbox[1]) + 10

        out_path = os.path.join(output_dir, f"slide_{slide_number:02d}.png")
        img.save(out_path, "PNG")
        return out_path

    # Collect (title, body, bg_query) tuples from the carousel model
    slides_data: list[tuple[str, str, str]] = []

    def _add(title, content, query=None):
        slides_data.append((title or "", content or "", query or title or ""))

    if isinstance(carousel_data, EducationalContentCarousel):
        _add(carousel_data.cover.title, carousel_data.cover.content)
        for s in carousel_data.contents:
            _add(s.title, s.content)
        _add(carousel_data.call_to_action.title, carousel_data.call_to_action.content)

    elif isinstance(carousel_data, CaseStudyCarousel):
        _add(carousel_data.cover.title, carousel_data.cover.content)
        _add(carousel_data.challenge.title, carousel_data.challenge.content, "challenge")
        _add(carousel_data.solution.title, carousel_data.solution.content, "solution")
        _add(carousel_data.results.title, carousel_data.results.content, "success results")
        if carousel_data.testimonial:
            _add(carousel_data.testimonial.title, carousel_data.testimonial.content, "testimonial")
        _add(carousel_data.call_to_action.title, carousel_data.call_to_action.content)

    elif isinstance(carousel_data, PersonalStoryCarousel):
        _add(carousel_data.cover.title, carousel_data.cover.content)
        for s in carousel_data.story_slides:
            _add(s.title, s.content)
        _add(carousel_data.takeaway.title, carousel_data.takeaway.content)
        _add(carousel_data.call_to_action.title, carousel_data.call_to_action.content)

    elif isinstance(carousel_data, IndustryInsightsCarousel):
        _add(carousel_data.cover.title, carousel_data.cover.content)
        for s in carousel_data.insights:
            _add(s.title, s.content)
        _add(carousel_data.call_to_action.title, carousel_data.call_to_action.content)

    elif isinstance(carousel_data, EventRecapCarousel):
        _add(carousel_data.cover.title, carousel_data.cover.content)
        for s in carousel_data.key_moments:
            _add(s.title, s.content)
        _add(carousel_data.call_to_action.title, carousel_data.call_to_action.content)

    elif isinstance(carousel_data, TestimonialCarousel):
        _add(carousel_data.cover.title, carousel_data.cover.content)
        for s in carousel_data.testimonials:
            _add(s.title, s.content, "testimonial client")
        _add(carousel_data.call_to_action.title, carousel_data.call_to_action.content)

    elif isinstance(carousel_data, ProductDemoCarousel):
        _add(carousel_data.cover.title, carousel_data.cover.content)
        _add(carousel_data.main_feature.title, carousel_data.main_feature.content, "product feature")
        for s in carousel_data.additional_features:
            _add(s.title, s.content, "product feature")
        _add(carousel_data.call_to_action.title, carousel_data.call_to_action.content)

    default_image = get_default_image_path()
    total = len(slides_data)
    image_paths = []
    for idx, (title, body, query) in enumerate(slides_data, start=1):
        bg = get_pexels_image_path(query, default_image) if idx in (1, total) else None
        path = _render_slide(idx, total, title, body, bg)
        image_paths.append(path)

    return image_paths


if __name__ == "__main__":
    # Debug
    # debug_master_slide_placeholders_and_text()

    # test_caption_only_slide()
    # test_create_educational_ppt()
    test_create_case_study_ppt()

    exit(0)

    # Example usage of the TestimonialCarousel model
    carousel_data = {
        "cover": {
            "title": "What Our Clients Are Saying",
            "content": "Hear from our satisfied clients about their experience "
        },
        "testimonials": [
            {
                "title": "Client Testimonial 1",
                "content": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                "image_url": "https://example.com/client1.jpg",
                "client_name": "John Doe",
                "client_logo_url": "https://example.com/logo1.jpg"
            },
            {
                "title": "Client Testimonial 2",
                "content": "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                "image_url": "https://example.com/client2.jpg",
                "client_name": "Jane Smith",
                "client_logo_url": "https://example.com/logo2.jpg"
            }
        ],
        "call_to_action": {
            "title": "Contact Us",
            "content": "If you are ready tto learn more about our services."
        }

    }
    ppt = create_ppt("Testimonials", TestimonialCarousel(**carousel_data))
    print(f"Presentation created: {ppt}")
