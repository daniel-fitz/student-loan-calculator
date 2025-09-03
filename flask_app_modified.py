from flask import Flask, render_template, request, jsonify
import math
from datetime import datetime

app = Flask(__name__)

def get_loan_details(plan_type):
    """
    Returns the repayment threshold, interest rate, and write-off period for each plan type
    Based on UK student loan system as of 2024/25
    """
    loan_plans = {
        1: {
            'threshold': 22015,
            'interest_rate': 0.075,
            'write_off_years': 25,
            'repayment_rate': 0.09
        },
        2: {
            'threshold': 27295,
            'interest_rate': 0.075,
            'write_off_years': 30,
            'repayment_rate': 0.09
        },
        4: {
            'threshold': 27660,
            'interest_rate': 0.075,
            'write_off_years': 30,
            'repayment_rate': 0.09
        },
        5: {
            'threshold': 25000,
            'interest_rate': 0.075,
            'write_off_years': 40,
            'repayment_rate': 0.09
        },
        'postgraduate': {
            'threshold': 21000,
            'interest_rate': 0.075,
            'write_off_years': 30,
            'repayment_rate': 0.06
        }
    }
    return loan_plans.get(plan_type)

def calculate_years_remaining_from_start_date(start_year, plan_type):
    """
    Calculate how many years are left based on when repayments started
    """
    plan_details = get_loan_details(plan_type)
    if not plan_details:
        return None
    
    current_year = datetime.now().year
    years_since_start = current_year - start_year
    write_off_years = plan_details['write_off_years']
    years_remaining = write_off_years - years_since_start
    
    return max(0, years_remaining)

def calculate_monthly_payment(salary, threshold, repayment_rate):
    """Calculate monthly repayment based on salary and threshold"""
    if salary <= threshold:
        return 0
    annual_repayment = (salary - threshold) * repayment_rate
    return annual_repayment / 12

def calculate_loan_repayment_with_time(balance, salary, plan_type, years_left, extra_monthly=0):
    """
    Calculate loan repayment details with detailed breakdown of payments
    """
    plan_details = get_loan_details(plan_type)
    if not plan_details:
        return None
    
    threshold = plan_details['threshold']
    interest_rate = plan_details['interest_rate']
    write_off_years = plan_details['write_off_years']
    repayment_rate = plan_details['repayment_rate']
    
    # Calculate monthly payment
    monthly_payment = calculate_monthly_payment(salary, threshold, repayment_rate)
    total_monthly_payment = monthly_payment + extra_monthly
    
    # Monthly interest rate
    monthly_interest = interest_rate / 12
    months_left = years_left * 12
    
    # Simulate loan over the specified time period
    remaining_balance = balance
    total_paid = 0
    total_interest_paid = 0
    total_principal_paid = 0
    total_extra_paid = extra_monthly * months_left  # Track total extra payments
    
    for month in range(int(months_left)):
        if remaining_balance <= 0:
            break
            
        # Calculate interest for this month
        interest_this_month = remaining_balance * monthly_interest
        
        # Calculate payment (can't pay more than balance + interest)
        payment_this_month = min(total_monthly_payment, remaining_balance + interest_this_month)
        
        # Calculate how much goes to principal vs interest
        interest_portion = min(interest_this_month, payment_this_month)
        principal_portion = payment_this_month - interest_portion
        
        # Update totals
        remaining_balance = remaining_balance + interest_this_month - payment_this_month
        total_paid += payment_this_month
        total_interest_paid += interest_portion
        total_principal_paid += principal_portion
    
    # Calculate net impact on balance
    initial_balance = balance
    net_impact_on_balance = initial_balance - remaining_balance
    
    # Adjust extra payments if loan paid off early
    if remaining_balance <= 0:
        months_actually_paid = 0
        test_balance = balance
        for month in range(int(months_left)):
            if test_balance <= 0:
                break
            months_actually_paid += 1
            interest_this_month = test_balance * monthly_interest
            payment_this_month = min(total_monthly_payment, test_balance + interest_this_month)
            test_balance = test_balance + interest_this_month - payment_this_month
        total_extra_paid = extra_monthly * months_actually_paid
    
    # Check if loan will be fully paid or written off
    if remaining_balance <= 0.01:  # Fully paid off
        return {
            'months_to_payoff': months_left,
            'total_paid': total_paid,
            'final_balance': 0,
            'written_off': False,
            'monthly_payment': total_monthly_payment,
            'years_left': years_left,
            'interest_paid': total_interest_paid,
            'principal_paid': total_principal_paid,
            'mandatory_payment_portion': monthly_payment,
            'extra_payment_portion': total_extra_paid,
            'net_impact_on_balance': net_impact_on_balance
        }
    else:
        # Will have remaining balance - check if it's write-off time
        return {
            'months_to_payoff': months_left,
            'total_paid': total_paid,
            'final_balance': max(0, remaining_balance),
            'written_off': years_left >= write_off_years,
            'monthly_payment': total_monthly_payment,
            'years_left': years_left,
            'interest_paid': total_interest_paid,
            'principal_paid': total_principal_paid,
            'mandatory_payment_portion': monthly_payment,
            'extra_payment_portion': total_extra_paid,
            'net_impact_on_balance': net_impact_on_balance
        }

def calculate_extra_payment_scenarios(balance, salary, plan_type, years_left):
    """Calculate various extra payment scenarios with detailed breakdowns"""
    plan_details = get_loan_details(plan_type)
    if not plan_details:
        return []
    
    monthly_interest = plan_details['interest_rate'] / 12
    months_left = years_left * 12
    base_monthly_payment = calculate_monthly_payment(salary, plan_details['threshold'], plan_details['repayment_rate'])
    
    # Get standard payment result
    standard_result = calculate_loan_repayment_with_time(balance, salary, plan_type, years_left)
    total_with_standard_payments = standard_result['total_paid']
    
    scenarios = []
    
    # Test different extra payment amounts
    for extra in [50, 100, 200, 500]:
        if base_monthly_payment + extra <= 0:
            continue
            
        # Calculate detailed breakdown with this extra payment
        result_with_extra = calculate_loan_repayment_with_time(balance, salary, plan_type, years_left, extra)
        
        if result_with_extra['final_balance'] <= 0.01:  # Loan gets paid off
            # Calculate actual time to payoff
            test_balance = balance
            months_to_payoff = 0
            
            for month in range(int(months_left)):
                if test_balance <= 0:
                    break
                
                interest = test_balance * monthly_interest
                payment = base_monthly_payment + extra
                payment_this_month = min(payment, test_balance + interest)
                
                test_balance = test_balance + interest - payment_this_month
                months_to_payoff += 1
                
                if test_balance <= 0.01:
                    break
            
            years_to_payoff = months_to_payoff / 12
            savings = total_with_standard_payments - result_with_extra['total_paid']
            
            scenarios.append({
                'extra_amount': extra,
                'years_to_payoff': years_to_payoff,
                'total_paid': result_with_extra['total_paid'],
                'interest_paid': result_with_extra['interest_paid'],
                'principal_paid': result_with_extra['principal_paid'],
                'extra_payments_total': extra * months_to_payoff,
                'savings': savings,
                'paid_off': True,
                'net_impact_on_balance': result_with_extra['net_impact_on_balance']
            })
        else:
            scenarios.append({
                'extra_amount': extra,
                'years_to_payoff': years_left,
                'total_paid': result_with_extra['total_paid'],
                'interest_paid': result_with_extra['interest_paid'],
                'principal_paid': result_with_extra['principal_paid'],
                'extra_payments_total': result_with_extra['extra_payment_portion'],
                'savings': total_with_standard_payments - result_with_extra['total_paid'],
                'paid_off': False,
                'net_impact_on_balance': result_with_extra['net_impact_on_balance']
            })
    
    return scenarios

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        
        balance = float(data['balance'])
        plan_type = data['plan_type']
        if plan_type == 'postgraduate':
            plan_type = 'postgraduate'
        else:
            plan_type = int(plan_type)
        
        salary = float(data['salary'])
        
        # Handle years left calculation
        if data['time_method'] == 'start_year':
            start_year = int(data['start_year'])
            years_left = calculate_years_remaining_from_start_date(start_year, plan_type)
            if years_left is None:
                return jsonify({'error': 'Invalid repayment plan selected'}), 400
            if years_left <= 0:
                return jsonify({'error': 'Your loan should already be written off!'}), 400
        else:
            years_left = float(data['years_left'])
        
        # Calculate standard repayment
        result = calculate_loan_repayment_with_time(balance, salary, plan_type, years_left)
        
        if not result:
            return jsonify({'error': 'Invalid repayment plan selected'}), 400
        
        # Get plan details
        plan_details = get_loan_details(plan_type)
        
        # Calculate extra payment scenarios
        scenarios = calculate_extra_payment_scenarios(balance, salary, plan_type, years_left)
        
        # Calculate custom extra payment if provided
        custom_result = None
        if 'extra_payment' in data and data['extra_payment']:
            extra_payment = float(data['extra_payment'])
            custom_result = calculate_loan_repayment_with_time(balance, salary, plan_type, years_left, extra_payment)
            
            # Calculate if it pays off early
            plan_details_temp = get_loan_details(plan_type)
            monthly_interest = plan_details_temp['interest_rate'] / 12
            base_monthly_payment = calculate_monthly_payment(salary, plan_details_temp['threshold'], plan_details_temp['repayment_rate'])
            
            test_balance = balance
            months_to_payoff = 0
            
            for month in range(int(years_left * 12)):
                if test_balance <= 0:
                    break
                
                interest = test_balance * monthly_interest
                payment = base_monthly_payment + extra_payment
                payment_this_month = min(payment, test_balance + interest)
                
                test_balance = test_balance + interest - payment_this_month
                months_to_payoff += 1
                
                if test_balance <= 0.01:
                    break
            
            custom_result['early_payoff'] = test_balance <= 0.01
            if custom_result['early_payoff']:
                custom_result['years_to_payoff'] = months_to_payoff / 12
                custom_result['savings'] = result['total_paid'] - custom_result['total_paid']
        
        return jsonify({
            'result': result,
            'plan_details': plan_details,
            'years_left': years_left,
            'scenarios': scenarios,
            'custom_result': custom_result
        })
        
    except (ValueError, KeyError) as e:
        return jsonify({'error': 'Please enter valid values'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)