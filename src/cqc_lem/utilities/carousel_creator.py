import os
import pprint
from typing import Optional, Union

from lxml.etree import tostring
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_xml
from pydantic import BaseModel, Field, HttpUrl, conlist
from pydantic_extra_types.color import Color


# Generic slide model for reusability
class Slide(BaseModel):
    title: str = Field(..., description="Title or heading of the slide")
    content: str = Field(..., description="Main content of the slide", max_length=500)
    image_url: Optional[HttpUrl] = Field(None, description="URL to an image for visual representation")


# Specific Carousel Templates

class EducationalContentSlide(Slide):
    # Custom Educational Content slides could have additional elements if needed
    pass


class EducationalContentCarousel(BaseModel):
    cover: EducationalContentSlide = Field(..., description="Cover Slide: A bold title that clearly states the topic.")
    contents: conlist(EducationalContentSlide, min_length=1, max_length=4) = Field(...,
                                                                                   description="Content Slides: Each slide covers one tip or step with a combination of short text and relevant visuals.")
    call_to_action: EducationalContentSlide = Field(...,
                                                    description="Final Slide: Summarize key points and add a call to action.")


class CaseStudySlide(Slide):
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


class PersonalStorySlide(Slide):
    # Custom personal story slide if needed
    pass


class PersonalStoryCarousel(BaseModel):
    cover: PersonalStorySlide = Field(..., description="Cover Slide: Compelling title introducing the personal story.")
    story_slides: conlist(PersonalStorySlide, min_length=1, max_length=3) = Field(...,
                                                                                  description="Slides 2-4: Key moments in the journey.")
    takeaway: PersonalStorySlide = Field(..., description="Slide 5: Summary or lessons learned from the experience.")
    call_to_action: PersonalStorySlide = Field(...,
                                               description="Final Slide: Encourage viewers to share their own stories or connect with you for further discussion.")


class IndustryInsightSlide(Slide):
    # Custom industry insight slide for trends and insights
    pass


class IndustryInsightsCarousel(BaseModel):
    cover: IndustryInsightSlide = Field(...,
                                        description="Cover Slide: Title with an attention-grabbing phrase for industry insights.")
    insights: conlist(IndustryInsightSlide, min_length=1, max_length=4) = Field(...,
                                                                                description="Slides 2-5: Individual trends or insights with visuals.")
    call_to_action: IndustryInsightSlide = Field(...,
                                                 description="Final Slide: Summary and call-to-action for opinions on the trends.")


class EventRecapSlide(Slide):
    # Custom event recap slide if additional details are needed
    pass


class EventRecapCarousel(BaseModel):
    cover: EventRecapSlide = Field(..., description="cover Slide: Event title and date.")
    key_moments: conlist(EventRecapSlide, min_length=1, max_length=3) = Field(...,
                                                                              description="Slides 2-4: Key takeaways or highlights from the event.")
    call_to_action: EventRecapSlide = Field(...,
                                            description="Final Slide: Thank attendees and provide a call-to-action for future events or download additional resources.")


class TestimonialSlide(Slide):
    client_name: str = Field(..., description="Name of the client providing the testimonial")
    client_logo_url: Optional[HttpUrl] = Field(None, description="URL to the client’s logo or photo")


class TestimonialCarousel(BaseModel):
    cover: Slide = Field(...,
                         description="Cover Slide: Cover slide with a title like 'What Our Clients Are Saying'.")
    testimonials: conlist(TestimonialSlide, min_length=1, max_length=3) = Field(...,
                                                                                description="Slides 2-4: Individual testimonials with a quote, client name, and photo.")
    call_to_action: Slide = Field(...,
                                  description="Final Slide: Call-to-action to encourage viewers to reach out for similar results.")


class ProductDemoSlide(Slide):
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
    slide_count = 0
    header = ""
    content = ""
    last_slide_layout_index = -1
    firsttime = True

    if isinstance(carousel_data, EducationalContentCarousel):
        # Handle EducationalContentCarousel
        pass
    elif isinstance(carousel_data, CaseStudyCarousel):
        # Handle CaseStudyCarousel
        pass
    elif isinstance(carousel_data, PersonalStoryCarousel):
        # Handle PersonalStoryCarousel
        pass
    elif isinstance(carousel_data, IndustryInsightsCarousel):
        # Handle IndustryInsightsCarousel
        pass
    elif isinstance(carousel_data, EventRecapCarousel):
        # Handle EventRecapCarousel
        pass
    elif isinstance(carousel_data, TestimonialCarousel):
        # Handle TestimonialCarousel

        # Add the Cover slide
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        title = slide.shapes.title
        title.text = carousel_data.cover.title
        body_shape = slide.shapes.placeholders[1]
        tf = body_shape.text_frame
        tf.text = carousel_data.cover.content

        # Add the testimonials
        for testimonial in carousel_data.testimonials:
            slide = prs.slides.add_slide(prs.slide_layouts[14])
            title = slide.shapes.title
            title.text = "—" + testimonial.client_name
            body_shape = slide.shapes.placeholders[1]
            tf = body_shape.text_frame
            tf.text = f'"{testimonial.content}"'

        # Add the Call to Action
        slide = prs.slides.add_slide(prs.slide_layouts[17])
        debug_slide(slide)
        title = slide.shapes.placeholders[0]
        ttf = title.text_frame
        ttf.text = carousel_data.call_to_action.title
        #title.text = carousel_data.call_to_action.title
        body_shape = slide.shapes.placeholders[1]
        tf = body_shape.text_frame
        tf.text = carousel_data.call_to_action.content

        pass
    elif isinstance(carousel_data, ProductDemoCarousel):
        # Handle ProductDemoCarousel
        pass

    file_path = os.path.join(generated_dir, f"{ppt_name}.pptx")
    prs.save(file_path)

    convert_ppt_theme_colors(file_path, my_theme)

    return f"{file_path}"

def debug_slide(slide):
    """ Print the placeholder and their indexes in a slide"""
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
            #print(f"{field_name} color before: {color_element.get('val')}")
            set_color = field_value.as_hex(format="long").replace("#", "")
            #print(f"{field_name} color after: {set_color}")
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
            #print(f"{theme_color_name} color before: {color_element.get('val')}")
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


if __name__ == "__main__":
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
