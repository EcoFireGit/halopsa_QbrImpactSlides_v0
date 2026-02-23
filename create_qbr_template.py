"""
QBR Template Generator for MSP Customer Success Tool (Business Impact Version)
Run this script to create Master_QBR_Template.pptx with the top 4 impact placeholders

Prerequisites:
    pip install python-pptx

Usage:
    python create_qbr_template.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Define color scheme
BLUE = RGBColor(46, 92, 138)  # #2E5C8A
GRAY = RGBColor(74, 85, 104)  # #4A5568
LIGHT_GRAY = RGBColor(226, 232, 240)


def add_title_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

    # Title
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1))
    title_frame = title_box.text_frame
    title_frame.text = "Quarterly Business Review"
    title_frame.paragraphs[0].font.size = Pt(48)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE
    title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Client Name
    client_box = slide.shapes.add_textbox(
        Inches(1), Inches(3.7), Inches(8), Inches(0.8)
    )
    client_frame = client_box.text_frame
    client_frame.text = "{{CLIENT_NAME}}"
    client_frame.paragraphs[0].font.size = Pt(32)
    client_frame.paragraphs[0].font.color.rgb = GRAY
    client_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Review Period
    period_box = slide.shapes.add_textbox(Inches(1), Inches(6), Inches(8), Inches(0.5))
    period_frame = period_box.text_frame
    period_frame.text = "{{REVIEW_PERIOD}}"
    period_frame.paragraphs[0].font.size = Pt(20)
    period_frame.paragraphs[0].font.color.rgb = GRAY
    period_frame.paragraphs[0].alignment = PP_ALIGN.CENTER


def add_executive_summary(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(9), Inches(0.8)
    )
    title_frame = title_box.text_frame
    title_frame.text = "Executive Summary"
    title_frame.paragraphs[0].font.size = Pt(40)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE

    # Content bullets focused on Business Impact
    content_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
    tf = content_box.text_frame
    tf.word_wrap = True

    bullets = [
        "{{SAME_DAY_RATE}}% of your team's IT issues were completely resolved on the same day.",
        "When employees reached out, we began working on their issues in an average of {{AVG_FIRST_RESPONSE}}.",
        "Critical business-halting emergencies were resolved in {{CRITICAL_RES_TIME}} on average.",
        "We managed {{TICKET_COUNT}} total IT events this quarter to keep your business running.",
    ]

    for i, bullet_text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + bullet_text
        p.font.size = Pt(22)
        p.font.color.rgb = GRAY
        p.space_after = Pt(24)


def add_metrics_overview(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(9), Inches(0.8)
    )
    title_frame = title_box.text_frame
    title_frame.text = "Key Business Impact Metrics"
    title_frame.paragraphs[0].font.size = Pt(40)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE

    # Three metric cards for the new metrics
    metrics = [
        ("Same-Day Resolution", "{{SAME_DAY_RATE}}%"),
        ("Avg First Response", "{{AVG_FIRST_RESPONSE}}"),
        ("Critical Resolution", "{{CRITICAL_RES_TIME}}"),
    ]

    x_positions = [1, 3.7, 6.4]
    for i, (label, value) in enumerate(metrics):
        # Card background
        card = slide.shapes.add_shape(
            1, Inches(x_positions[i]), Inches(2.5), Inches(2.2), Inches(2.5)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = LIGHT_GRAY
        card.line.color.rgb = BLUE

        # Label
        label_box = slide.shapes.add_textbox(
            Inches(x_positions[i]), Inches(2.7), Inches(2.2), Inches(0.8)
        )
        label_frame = label_box.text_frame
        label_frame.text = label
        label_frame.paragraphs[0].font.size = Pt(14)
        label_frame.paragraphs[0].font.color.rgb = GRAY
        label_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

        # Value
        value_box = slide.shapes.add_textbox(
            Inches(x_positions[i]), Inches(3.5), Inches(2.2), Inches(1)
        )
        value_frame = value_box.text_frame
        value_frame.text = value
        value_frame.paragraphs[0].font.size = Pt(26)
        value_frame.paragraphs[0].font.bold = True
        value_frame.paragraphs[0].font.color.rgb = BLUE
        value_frame.paragraphs[0].alignment = PP_ALIGN.CENTER


def add_chart_placeholder(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(9), Inches(0.8)
    )
    title_frame = title_box.text_frame
    title_frame.text = "Support Type Distribution"
    title_frame.paragraphs[0].font.size = Pt(40)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE

    # Subtitle
    subtitle_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(1.3), Inches(9), Inches(0.4)
    )
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.text = "Proactive Maintenance vs Reactive Support"
    subtitle_frame.paragraphs[0].font.size = Pt(20)
    subtitle_frame.paragraphs[0].font.color.rgb = GRAY

    # Chart placeholder box
    placeholder = slide.shapes.add_shape(
        1, Inches(2), Inches(2.5), Inches(6), Inches(4)
    )
    placeholder.fill.solid()
    placeholder.fill.fore_color.rgb = RGBColor(240, 240, 240)
    placeholder.line.color.rgb = GRAY

    # Placeholder text
    text_box = slide.shapes.add_textbox(Inches(2), Inches(4), Inches(6), Inches(1))
    text_frame = text_box.text_frame
    text_frame.text = "{{CHART_PLACEHOLDER}}"
    text_frame.paragraphs[0].font.size = Pt(24)
    text_frame.paragraphs[0].font.color.rgb = GRAY
    text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER


def add_stability_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(9), Inches(0.8)
    )
    title_frame = title_box.text_frame
    title_frame.text = "System Stability (Metric 1)"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE

    # Left box - Proactive
    left_box = slide.shapes.add_shape(1, Inches(1), Inches(2.5), Inches(3.5), Inches(2))
    left_box.fill.solid()
    left_box.fill.fore_color.rgb = RGBColor(34, 197, 94)  # Green

    left_text = slide.shapes.add_textbox(
        Inches(1), Inches(2.7), Inches(3.5), Inches(1.5)
    )
    left_frame = left_text.text_frame
    left_frame.text = "Proactive Work\n{{PROACTIVE_PERCENT}}%"
    left_frame.paragraphs[0].font.size = Pt(28)
    left_frame.paragraphs[0].font.bold = True
    left_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
    left_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Right box - Reactive
    right_box = slide.shapes.add_shape(
        1, Inches(5.5), Inches(2.5), Inches(3.5), Inches(2)
    )
    right_box.fill.solid()
    right_box.fill.fore_color.rgb = RGBColor(239, 68, 68)  # Red

    right_text = slide.shapes.add_textbox(
        Inches(5.5), Inches(2.7), Inches(3.5), Inches(1.5)
    )
    right_frame = right_text.text_frame
    right_frame.text = "Reactive Issues\n{{REACTIVE_PERCENT}}%"
    right_frame.paragraphs[0].font.size = Pt(28)
    right_frame.paragraphs[0].font.bold = True
    right_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
    right_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Explanation
    exp_box = slide.shapes.add_textbox(Inches(1), Inches(5.5), Inches(8), Inches(1))
    exp_frame = exp_box.text_frame
    exp_frame.text = "We actively prevent downtime before it impacts your employees. A higher proactive percentage means a more stable network."
    exp_frame.paragraphs[0].font.size = Pt(16)
    exp_frame.paragraphs[0].font.color.rgb = GRAY
    exp_frame.paragraphs[0].alignment = PP_ALIGN.CENTER


def add_responsiveness_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(9), Inches(0.8)
    )
    title_frame = title_box.text_frame
    title_frame.text = "Responsiveness & Business Continuity"
    title_frame.paragraphs[0].font.size = Pt(36)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE

    # Content bullets focused on Metrics 2, 3, and 4
    content_box = slide.shapes.add_textbox(
        Inches(1.5), Inches(2.5), Inches(7), Inches(3.5)
    )
    tf = content_box.text_frame
    tf.word_wrap = True

    bullets = [
        "Speed to First Response: {{AVG_FIRST_RESPONSE}}",
        "Same-Day Resolution Rate: {{SAME_DAY_RATE}}%",
        "Critical Crisis Resolution Time: {{CRITICAL_RES_TIME}}",
    ]

    for i, bullet_text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + bullet_text
        p.font.size = Pt(26)
        p.font.color.rgb = GRAY
        p.space_after = Pt(30)


def add_recommendations(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(9), Inches(0.8)
    )
    title_frame = title_box.text_frame
    title_frame.text = "Strategic Recommendations"
    title_frame.paragraphs[0].font.size = Pt(40)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE

    # Three recommendation boxes
    y_positions = [2, 3.5, 5]
    for i in range(3):
        # Number circle
        circle = slide.shapes.add_shape(
            1, Inches(1.2), Inches(y_positions[i]), Inches(0.5), Inches(0.5)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = BLUE

        num_text = slide.shapes.add_textbox(
            Inches(1.2), Inches(y_positions[i]), Inches(0.5), Inches(0.5)
        )
        num_frame = num_text.text_frame
        num_frame.text = str(i + 1)
        num_frame.paragraphs[0].font.size = Pt(24)
        num_frame.paragraphs[0].font.bold = True
        num_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
        num_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

        # Recommendation text
        rec_box = slide.shapes.add_textbox(
            Inches(2), Inches(y_positions[i]), Inches(6.5), Inches(0.8)
        )
        rec_frame = rec_box.text_frame
        rec_frame.text = f"{{{{RECOMMENDATION_{i + 1}}}}}"
        rec_frame.paragraphs[0].font.size = Pt(18)
        rec_frame.paragraphs[0].font.color.rgb = GRAY


def add_thank_you(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Thank you text
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1))
    title_frame = title_box.text_frame
    title_frame.text = "Thank You"
    title_frame.paragraphs[0].font.size = Pt(48)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = BLUE
    title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Contact prompt
    contact_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(8), Inches(0.6))
    contact_frame = contact_box.text_frame
    contact_frame.text = "Questions? Contact your account manager"
    contact_frame.paragraphs[0].font.size = Pt(22)
    contact_frame.paragraphs[0].font.color.rgb = GRAY
    contact_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Contact info placeholder
    info_box = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(8), Inches(1))
    info_frame = info_box.text_frame
    info_frame.text = "{{MSP_CONTACT_INFO}}"
    info_frame.paragraphs[0].font.size = Pt(18)
    info_frame.paragraphs[0].font.color.rgb = GRAY
    info_frame.paragraphs[0].alignment = PP_ALIGN.CENTER


def main():
    # Create presentation
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Build all slides
    print("Creating Impact-focused slides...")
    add_title_slide(prs)
    add_executive_summary(prs)
    add_metrics_overview(prs)
    add_chart_placeholder(prs)
    add_stability_slide(prs)
    add_responsiveness_slide(prs)  # Replaced SLA performance slide with this
    add_recommendations(prs)
    add_thank_you(prs)

    # Save the presentation
    filename = "Master_QBR_Template.pptx"
    prs.save(filename)
    print(f"✅ Business Impact QBR Template created successfully: {filename}")
    print("\n📋 Placeholders you need to populate with HaloPSA data:")
    placeholders = [
        "{{CLIENT_NAME}}",
        "{{REVIEW_PERIOD}}",
        "{{TICKET_COUNT}}",
        "{{PROACTIVE_PERCENT}}",
        "{{REACTIVE_PERCENT}}",
        "{{SAME_DAY_RATE}}",
        "{{AVG_FIRST_RESPONSE}}",
        "{{CRITICAL_RES_TIME}}",
        "{{CHART_PLACEHOLDER}}",
        "{{RECOMMENDATION_1}}",
        "{{RECOMMENDATION_2}}",
        "{{RECOMMENDATION_3}}",
        "{{MSP_CONTACT_INFO}}",
    ]
    for p in placeholders:
        print(f"   • {p}")


if __name__ == "__main__":
    main()
