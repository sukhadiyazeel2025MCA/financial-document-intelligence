import json
from google import genai
from google.genai import types
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PROMPTS = {
    'invoice': '''Extract invoice_number, invoice_date, due_date, vendor_name, vendor_address, customer_name, customer_address, currency, subtotal, tax_amount, tax_rate, discount, total_amount, payment_method, payment_terms, line_items (description, quantity, unit_price, amount, hsn_sac, tax_rate), notes, and any other visible fields. For each field, provide value, page_number, and source_text.''',
    'balance_sheet': '''Extract company_name, report_title, reporting_date, period, currency, auditor, and ALL financial line items organized by category (assets, liabilities, equity). For each line item, provide label, schedule (if present), values for each period/year visible, and page_number. Extract total_assets and total_capital_and_liabilities per period. If total_liabilities or total_equity are stated or can be summed from their categories, provide them per period; otherwise do not include null fields.''',
    'profit_and_loss': '''Extract company_name, report_title, period, currency, and ALL income/expense line items. Extract revenue, cost_of_sales, gross_profit, operating_expenses (itemized), operating_profit, interest_earned, other_income, total_income, interest_expended, provisions_and_contingencies, total_expenditure, profit_before_tax, tax, net_profit, minority_interest, consolidated_net_profit, brought_forward_profit, total_available_for_appropriation, appropriations. For each, provide values per period.''',
    'cash_flow_statement': '''Extract company_name, report_title, period, currency, and ALL cash flow line items organized by operating/investing/financing activities. Extract operating_cash_flow, investing_cash_flow, financing_cash_flow, fx_adjustment, net_change_in_cash, opening_cash, closing_cash, cash_acquired_on_amalgamation. For each, provide values per period. Brackets/parentheses = negative values.'''
}

class ExtractionService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def extract(self, text: str, images: list[bytes], document_type: str, filename: str) -> dict:
        prompt_text = PROMPTS.get(document_type, "Extract all key-value pairs.")
        contents = [prompt_text]
        
        if images:
            for img_bytes in images:
                mime = 'image/png' if img_bytes.startswith(b'\x89PNG') else 'image/jpeg'
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
        
        if text:
            contents.append(text)

        logger.info(f"Extracting data using Gemini for {filename} (type: {document_type})")
        
        models_to_try = [
            getattr(settings, 'GEMINI_MODEL', 'gemini-3.6-flash'),
            'gemini-3.8-flash',
            'gemini-3.5-flash',
            'gemini-flash-latest',
            'gemini-3.5-flash-lite'
        ]
        # Remove duplicates preserving order
        unique_models = []
        for m in models_to_try:
            if m not in unique_models:
                unique_models.append(m)

        last_error = None
        import time

        for model_name in unique_models:
            for attempt in range(2):
                try:
                    logger.info(f"Attempting extraction with model: {model_name} (attempt {attempt + 1})")
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type='application/json',
                            temperature=0.1,
                        )
                    )
                    return json.loads(response.text)
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    logger.warning(f"Model {model_name} failed attempt {attempt + 1}: {err_str}")
                    if "503" in err_str or "429" in err_str:
                        time.sleep(1.5)
                        continue
                    else:
                        break

        logger.error(f"All Gemini models failed: {str(last_error)}")
        raise last_error
