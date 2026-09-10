from app.schemas.document import ValidationResult, ValidationCheck
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class FinancialValidationService:
    def validate(self, extracted_data: dict, document_type: str) -> ValidationResult:
        result = ValidationResult(checks=[], issues=[])
        
        if document_type == 'invoice':
            self._validate_invoice(extracted_data, result)
        elif document_type == 'balance_sheet':
            self._validate_balance_sheet(extracted_data, result)
        elif document_type == 'profit_and_loss':
            self._validate_profit_and_loss(extracted_data, result)
        elif document_type == 'cash_flow_statement':
            self._validate_cash_flow(extracted_data, result)

        if any(c.status == 'FAIL' for c in result.checks):
            result.overall_status = 'FAIL'
        elif any(c.status == 'PASS' for c in result.checks):
            result.overall_status = 'PASS'
        else:
            result.overall_status = 'NOT_APPLICABLE'

        return result

    def _parse_num(self, val) -> float | None:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, dict):
            if 'value' in val:
                return self._parse_num(val['value'])
            return None
        try:
            s = str(val).strip().replace(',', '').replace('$', '').replace('€', '').replace('£', '').replace('INR', '').strip()
            if not s:
                return None
            # Handle parenthesis negative e.g. (1,234.50) -> -1234.50
            if s.startswith('(') and s.endswith(')'):
                return -float(s[1:-1].strip())
            return float(s)
        except (ValueError, TypeError):
            return None

    def _get_numeric_value(self, data: dict, field_path: str, period: str | None = None) -> float | None:
        keys = field_path.split('.')
        val = data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return None
        
        if isinstance(val, dict):
            if period and period in val:
                return self._parse_num(val[period])
            if 'value' in val:
                return self._parse_num(val['value'])
        
        return self._parse_num(val)

    def _find_numeric(self, data: dict, candidate_keys: list[str], period: str | None = None) -> float | None:
        # Check direct keys
        for key in candidate_keys:
            val = self._get_numeric_value(data, key, period)
            if val is not None:
                return val
        
        # Check inside financial_data or financial_line_items or other common nested containers
        for container_key in ['financial_data', 'financial_line_items', 'income', 'expenditure', 'profit']:
            if container_key in data and isinstance(data[container_key], dict):
                sub = data[container_key]
                for key in candidate_keys:
                    val = self._get_numeric_value(sub, key, period)
                    if val is not None:
                        return val
                # Check 2 levels deep (e.g. financial_data.income.total_income)
                for sub_container in sub.values():
                    if isinstance(sub_container, dict):
                        for key in candidate_keys:
                            val = self._get_numeric_value(sub_container, key, period)
                            if val is not None:
                                return val
        return None

    def _get_periods(self, data: dict) -> list[str]:
        # Check if periods list is explicitly provided
        if 'periods' in data and isinstance(data['periods'], list) and data['periods']:
            return [str(x) for x in data['periods'] if str(x).strip()]

        # Prioritize actual numeric dictionary keys from financial totals
        for k in ['total_assets', 'total_capital_and_liabilities', 'total_income', 'total_expenditure', 'net_profit', 'closing_cash']:
            if k in data and isinstance(data[k], dict):
                periods = [str(x) for x in data[k].keys() if x != 'value' and str(x).strip()]
                if periods:
                    return periods

        # Check inside financial_data (e.g. financial_data.income.total_income)
        if 'financial_data' in data and isinstance(data['financial_data'], dict):
            for sec_name, sec_val in data['financial_data'].items():
                if isinstance(sec_val, dict):
                    for item_k, item_v in sec_val.items():
                        if isinstance(item_v, dict):
                            keys = [str(x) for x in item_v.keys() if x not in ('schedule', 'value', 'label') and str(x).strip()]
                            if keys:
                                return keys

        # Check financial_line_items for column periods
        if 'financial_line_items' in data and isinstance(data['financial_line_items'], dict):
            for cat, items in data['financial_line_items'].items():
                if isinstance(items, list) and items:
                    for item in items:
                        if isinstance(item, dict) and 'values' in item and isinstance(item['values'], dict):
                            periods = [str(x) for x in item['values'].keys() if str(x).strip()]
                            if periods:
                                return periods

        # Fallback to period property
        if 'period' in data:
            p = data['period']
            if isinstance(p, list):
                return [str(x) for x in p]
            elif isinstance(p, str) and ',' in p:
                return [x.strip() for x in p.split(',')]
            elif isinstance(p, str):
                return [p]
        return [None]

    def _create_check(self, name: str, formula: str, operands: dict, calculated: float, reported: float, tolerance: float) -> ValidationCheck:
        variance = abs(calculated - reported) / max(abs(reported), 1.0)
        status = 'PASS' if variance <= tolerance else 'FAIL'
        message = 'Match' if status == 'PASS' else f'Mismatch: expected {calculated}, reported {reported}'
        return ValidationCheck(
            name=name, formula=formula, operands=operands,
            calculated_value=calculated, reported_value=reported,
            variance=variance, status=status, message=message
        )

    def _validate_invoice(self, data: dict, result: ValidationResult):
        subtotal = self._get_numeric_value(data, 'subtotal')
        tax = self._get_numeric_value(data, 'tax_amount') or 0.0
        discount = self._get_numeric_value(data, 'discount') or 0.0
        total = self._get_numeric_value(data, 'total_amount')

        if subtotal is not None and total is not None:
            calc_total = subtotal + tax - discount
            check = self._create_check(
                'invoice_total_check', 'subtotal + tax_amount - discount = total_amount',
                {'subtotal': subtotal, 'tax': tax, 'discount': discount},
                calc_total, total, settings.FINANCIAL_TOLERANCE
            )
            result.checks.append(check)
            if check.status == 'FAIL':
                result.issues.append(check.message)

        # Line items sum check
        line_items = data.get('line_items')
        if isinstance(line_items, list) and line_items:
            item_amounts = []
            for item in line_items:
                amt = self._get_numeric_value(item, 'amount')
                qty = self._get_numeric_value(item, 'quantity')
                unit_p = self._get_numeric_value(item, 'unit_price')
                if amt is not None:
                    item_amounts.append(amt)
                elif qty is not None and unit_p is not None:
                    item_amounts.append(qty * unit_p)
            
            if item_amounts and subtotal is not None:
                sum_lines = sum(item_amounts)
                check = self._create_check(
                    'line_items_subtotal_check', 'sum(line_item_amounts) = subtotal',
                    {'line_item_count': len(item_amounts), 'sum_line_items': sum_lines},
                    sum_lines, subtotal, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

    def _validate_balance_sheet(self, data: dict, result: ValidationResult):
        periods = self._get_periods(data)
        for period in periods:
            period_label = f" ({period})" if period else ""
            assets = self._get_numeric_value(data, 'total_assets', period)
            cap_liab = self._get_numeric_value(data, 'total_capital_and_liabilities', period)
            liab = self._get_numeric_value(data, 'total_liabilities', period)
            equity = self._get_numeric_value(data, 'total_equity', period)

            # Rule 1: Total Assets ≈ Total Capital and Liabilities
            if assets is not None and cap_liab is not None:
                check = self._create_check(
                    f'balance_equation{period_label}',
                    'total_assets = total_capital_and_liabilities',
                    {'total_assets': assets, 'total_capital_and_liabilities': cap_liab},
                    assets, cap_liab, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)
            elif assets is not None and liab is not None and equity is not None:
                # Rule 1 alternative: Assets = Liabilities + Equity
                calc_total = liab + equity
                check = self._create_check(
                    f'balance_equation{period_label}',
                    'total_liabilities + total_equity = total_assets',
                    {'total_liabilities': liab, 'total_equity': equity},
                    calc_total, assets, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

            # Rule 2: Component validation if liabilities + equity match capital_and_liabilities
            if liab is not None and equity is not None and cap_liab is not None:
                calc_cap = liab + equity
                check = self._create_check(
                    f'capital_and_liabilities_components{period_label}',
                    'total_liabilities + total_equity = total_capital_and_liabilities',
                    {'total_liabilities': liab, 'total_equity': equity},
                    calc_cap, cap_liab, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

            # Rule 3: Reconcile sum of Capital & Liabilities line items to reported total
            fin_items = data.get('financial_line_items') or data.get('line_items') or {}
            cap_liab_items = []
            if isinstance(fin_items, dict):
                # Banking / standard balance sheet format: Equity/Capital schedules + Liabilities schedules
                for grp in ['equity', 'capital', 'capital_and_reserves', 'liabilities']:
                    if isinstance(fin_items.get(grp), list):
                        cap_liab_items.extend(fin_items[grp])
            elif isinstance(data.get('capital_and_liabilities'), list):
                cap_liab_items = data.get('capital_and_liabilities')

            if cap_liab_items and cap_liab is not None:
                item_sum = 0.0
                counted = 0
                for it in cap_liab_items:
                    v = self._get_numeric_value(it, 'values', period) if isinstance(it, dict) and 'values' in it else self._get_numeric_value(it, 'value')
                    if v is not None:
                        item_sum += v
                        counted += 1
                if counted >= 2:
                    check = self._create_check(
                        f'capital_and_liabilities_sum{period_label}',
                        'sum(capital_and_liabilities_line_items) = total_capital_and_liabilities',
                        {'line_items_counted': counted, 'sum': item_sum},
                        item_sum, cap_liab, settings.FINANCIAL_TOLERANCE
                    )
                    result.checks.append(check)
                    if check.status == 'FAIL':
                        result.issues.append(check.message)

            # Rule 4: Reconcile sum of Assets line items to reported total assets
            for list_key in ['assets', 'financial_line_items.assets']:
                items = data.get(list_key) if '.' not in list_key else data.get('financial_line_items', {}).get('assets')
                if isinstance(items, list) and items and assets is not None:
                    item_sum = 0.0
                    counted = 0
                    for it in items:
                        v = self._get_numeric_value(it, 'values', period) if isinstance(it, dict) and 'values' in it else self._get_numeric_value(it, 'value')
                        if v is not None:
                            item_sum += v
                            counted += 1
                    if counted >= 2:
                        check = self._create_check(
                            f'assets_sum{period_label}',
                            'sum(assets_line_items) = total_assets',
                            {'line_items_counted': counted, 'sum': item_sum},
                            item_sum, assets, settings.FINANCIAL_TOLERANCE
                        )
                        result.checks.append(check)
                        if check.status == 'FAIL':
                            result.issues.append(check.message)
                        break

    def _validate_profit_and_loss(self, data: dict, result: ValidationResult):
        periods = self._get_periods(data)
        for period in periods:
            period_label = f" ({period})" if period else ""
            income = self._find_numeric(data, ['total_income', 'total_revenue', 'income.total_income'], period)
            expenditure = self._find_numeric(data, ['total_expenditure', 'total_expenses', 'expenditure.total_expenditure'], period)
            profit = self._find_numeric(data, ['net_profit_for_the_year', 'net_profit', 'profit.net_profit_for_the_year', 'consolidated_profit_for_the_year_attributable_to_the_group'], period)
            
            # Rule 1: Net Profit = Total Income - Total Expenditure
            if income is not None and expenditure is not None and profit is not None:
                calc_profit = income - expenditure
                check = self._create_check(
                    f'net_profit_check{period_label}',
                    'total_income - total_expenditure = net_profit',
                    {'total_income': income, 'total_expenditure': expenditure},
                    calc_profit, profit, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

            # Rule 2: Total Income = sum of income line items (Interest earned + Other income)
            interest_earned = self._find_numeric(data, ['interest_earned', 'income.interest_earned'], period)
            other_income = self._find_numeric(data, ['other_income', 'income.other_income'], period)
            if interest_earned is not None and other_income is not None and income is not None:
                calc_inc = interest_earned + other_income
                check = self._create_check(
                    f'income_sum_check{period_label}',
                    'interest_earned + other_income = total_income',
                    {'interest_earned': interest_earned, 'other_income': other_income},
                    calc_inc, income, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

            # Rule 3: Total Expenditure = sum of expenditure line items
            interest_exp = self._find_numeric(data, ['interest_expended', 'expenditure.interest_expended'], period)
            operating_exp = self._find_numeric(data, ['operating_expenses', 'expenditure.operating_expenses'], period)
            provisions = self._find_numeric(data, ['provisions_and_contingencies', 'expenditure.provisions_and_contingencies'], period)
            if interest_exp is not None and operating_exp is not None and provisions is not None and expenditure is not None:
                calc_exp = interest_exp + operating_exp + provisions
                check = self._create_check(
                    f'expenditure_sum_check{period_label}',
                    'interest_expended + operating_expenses + provisions = total_expenditure',
                    {'interest_expended': interest_exp, 'operating_expenses': operating_exp, 'provisions': provisions},
                    calc_exp, expenditure, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

            # Rule 4: Gross Profit = Revenue - Cost of Sales (for corporate P&L)
            rev = self._find_numeric(data, ['revenue', 'sales'], period)
            cogs = self._find_numeric(data, ['cost_of_sales', 'cogs'], period)
            gross = self._find_numeric(data, ['gross_profit'], period)
            if rev is not None and cogs is not None and gross is not None:
                calc_gross = rev - cogs
                check = self._create_check(
                    f'gross_profit_check{period_label}',
                    'revenue - cost_of_sales = gross_profit',
                    {'revenue': rev, 'cost_of_sales': cogs},
                    calc_gross, gross, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

    def _validate_cash_flow(self, data: dict, result: ValidationResult):
        periods = self._get_periods(data)
        for period in periods:
            period_label = f" ({period})" if period else ""
            operating = self._get_numeric_value(data, 'operating_cash_flow', period)
            investing = self._get_numeric_value(data, 'investing_cash_flow', period)
            financing = self._get_numeric_value(data, 'financing_cash_flow', period)
            fx = self._get_numeric_value(data, 'fx_adjustment', period) or 0.0
            net_change = self._get_numeric_value(data, 'net_change_in_cash', period)
            opening = self._get_numeric_value(data, 'opening_cash', period)
            closing = self._get_numeric_value(data, 'closing_cash', period)

            if None not in (operating, investing, financing, net_change):
                calc_change = operating + investing + financing + fx
                check = self._create_check(
                    f'net_change_in_cash_check{period_label}',
                    'operating + investing + financing + fx = net_change_in_cash',
                    {'operating': operating, 'investing': investing, 'financing': financing, 'fx': fx},
                    calc_change, net_change, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

            if opening is not None and net_change is not None and closing is not None:
                calc_close = opening + net_change
                check = self._create_check(
                    f'closing_cash_check{period_label}',
                    'opening_cash + net_change_in_cash = closing_cash',
                    {'opening_cash': opening, 'net_change_in_cash': net_change},
                    calc_close, closing, settings.FINANCIAL_TOLERANCE
                )
                result.checks.append(check)
                if check.status == 'FAIL':
                    result.issues.append(check.message)

