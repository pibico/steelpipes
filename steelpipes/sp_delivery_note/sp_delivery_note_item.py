import frappe
from frappe.utils import flt, get_datetime, getdate, add_days, date_diff, nowdate, today
from frappe.model.document import Document


@frappe.whitelist()
def calculate_pipe_weight_um(itemcode, um):
    # Calculating Pipe Weight using Attributes

    delivery_note_item_um = frappe.get_doc("Item", itemcode)
    item_thickness_um = item_width_um = item_length_um = 0
    if str(delivery_note_item_um.variant_of) in ['Pipe']:
        for item_attribute_um in delivery_note_item_um.attributes:
            attribute_name = str(item_attribute_um.attribute)
            if 'Thickness' in attribute_name:
                item_thickness_um = float(item_attribute_um.attribute_value)
            if 'Width' in attribute_name:
                item_width_um = float(item_attribute_um.attribute_value)
            if 'Length' in attribute_name:
                item_length_um = float(item_attribute_um.attribute_value)

        item_weight_um = (1.2 * item_thickness_um * item_width_um * item_length_um) / 508
        if um == 'Meter':
            item_length_um = item_length_um * 0.3048
        return {"item_weight_um": round(item_weight_um, 2), "item_length_um": round(item_length_um, 2)}


def update_pipe_weight_um(self, cdt):
    estimate_weight_um_temp = 0
    total_um_temp = 0
    total_temp = 0
    discount_temp = 0
    total_scale_weight_um_temp = 0
    weight_difference_um_temp = 0
    weight_difference_percentage_um_temp = 0
    has_pipe = 0,

    for d in self.items:
        if 'Pipe-MS' in str(d.item_code):
            qty_temp = 0
            if d.qty <0:
                qty_temp = d.qty*-1
                if d.rate_um_per_qty <=0:
                    d.rate_um_per_qty = d.rate_um_per_qty*-1
                else:
                    d.rate_um_per_qty = d.rate_um_per_qty*1    
            else:
                qty_temp = d.qty
                d.rate_um_per_qty = d.rate_um_per_qty
             
            d.amount_um                  = d.qty*d.rate_um_per_qty
            d.total_scale_weight_um      = qty_temp*d.scale_weight_um
            d.total_weight_um            = qty_temp*d.weight_um
            d.total_length_um            = qty_temp*d.length_um
            
            total_um_temp               += d.amount_um
            total_temp                  += d.amount
            total_scale_weight_um_temp  += d.total_scale_weight_um
            estimate_weight_um_temp     += d.total_weight_um
            has_pipe = 1


    if has_pipe == 1:
        self.total_weight_um                    = self.loaded_vehicle_weight_um - self.empty_vehicle_weight_um
        weight_difference_um_temp               = self.total_weight_um - estimate_weight_um_temp
        weight_difference_percentage_um_temp    = (weight_difference_um_temp / estimate_weight_um_temp) * 100
        discount_temp                           = total_temp - total_um_temp

        self.estimate_weight_um                 = estimate_weight_um_temp
        self.total_um                           = total_um_temp
        self.weight_difference_um               = weight_difference_um_temp
        self.weight_difference_percentage_um    = weight_difference_percentage_um_temp
        self.total_scale_weight_um              = total_scale_weight_um_temp
        if self.apply_auto_discount ==1:
            self.apply_discount_on                  = 'Net Total'
            self.discount_amount                    = discount_temp
            
    else:
        self.estimate_weight_um                 = 0
        self.total_um                           = 0
        self.weight_difference_um               = 0
        self.weight_difference_percentage_um    = 0
        self.total_scale_weight_um              = 0
        self.empty_vehicle_weight_um            = 0
        self.loaded_vehicle_weight_um           = 0
        self.total_weight_um                    = 0
    self.calculate_taxes_and_totals()
    if (self.set_posting_time == None or self.set_posting_time == 0):
        self.posting_date = add_days(today(),-1)
        

def validate_weight_threshold(self, cdt):
    show_instructions_1 = 0
    show_instructions_2 = 0
    show_exception = 0
    weight_difference_um_temp = 0
    weight_difference_percentage_um_temp = 0
    has_pipe = 0
    if self.has_weight == 1:
        for d in self.items:
            if 'Pipe-MS' in str(d.item_code):
                if self.doctype == 'Purchase Receipt' or (self.doctype == 'Stock Entry' and (self.stock_entry_type == 'Send to Warehouse' or self.stock_entry_type == 'Receive at Warehouse')):
                    item = frappe.get_doc('Item',d.item_code)
                    item.db_set('last_weight_received',d.scale_weight_um)
                    item.db_set('last_quantity_received',d.qty)
                if self.doctype == 'Delivery Note':
                    item = frappe.get_doc('Item',d.item_code)
                    item.db_set('last_weight_delivered',d.scale_weight_um)
                    item.db_set('last_quantity_delivered',d.qty)

                has_pipe = 1
                weight_difference_um_temp               = round((d.scale_weight_um - d.weight_um),2)
                weight_difference_percentage_um_temp    = round((weight_difference_um_temp / d.weight_um) * 100, 2)
                if weight_difference_percentage_um_temp < -3 or weight_difference_percentage_um_temp > 3 or d.scale_weight_um == 0:
                    show_exception = 1

                    if d.scale_weight_um == 0:
                        frappe.msgprint("Scale Weight for {0} is missing".format(d.item_name))
                        show_instructions_1 = 1

                    elif weight_difference_percentage_um_temp > 0:
                        frappe.msgprint("{0} weight exceeds by {1}%".format(d.item_name,
                        weight_difference_percentage_um_temp) + " and {0}Kg".format(weight_difference_um_temp))
                        show_instructions_2 = 1

                    elif weight_difference_percentage_um_temp < 0:
                        weight_difference_percentage_um_temp    = weight_difference_percentage_um_temp * -1
                        weight_difference_um_temp               = weight_difference_um_temp * -1 
                        frappe.msgprint("{0} weight is less by {1}%".format(d.item_name,
                        weight_difference_percentage_um_temp) + " and {0}Kg".format(weight_difference_um_temp))
                        show_instructions_2 = 1

        self_weight_difference_um_temp              = self.weight_difference_um
        self_weight_difference_percentage_um_temp   = round(self.weight_difference_percentage_um, 2)
        if has_pipe == 1:
            if self.weight_difference_percentage_um < -3 or self.weight_difference_percentage_um > 3 or self.loaded_vehicle_weight_um == 0:
                show_exception = 1

                if self.loaded_vehicle_weight_um == 0:
                    frappe.msgprint("Loaded Vehicle Weight is missing")
                    show_instructions_1 = 1

                elif self.weight_difference_percentage_um > 0:
                    frappe.msgprint("Net Weight exceeds by {0}%".format(self_weight_difference_percentage_um_temp) 
                    + "and {0}Kg ".format(self_weight_difference_um_temp))
                    show_instructions_2 = 1

                elif self.weight_difference_percentage_um < 0:
                    self_weight_difference_um_temp = self_weight_difference_um_temp * -1
                    self_weight_difference_percentage_um_temp = self_weight_difference_percentage_um_temp * -1
                    frappe.msgprint("Net Weight is less by {0}%".format(self_weight_difference_percentage_um_temp) 
                    + " and {0}Kg ".format(self_weight_difference_um_temp))
                    show_instructions_2 = 1
    
    else:
        show_exception = 0

    if show_exception == 1:
        if show_instructions_1 == 1 and show_instructions_2 == 0:
            frappe.throw("Please enter values for the above!")
        elif show_instructions_1 == 0 and show_instructions_2 == 1:
            frappe.throw("Please verify weight!")
        else:
            frappe.throw("Please verify weight and enter the missing values!")
    elif self.has_weight == 0 or show_exception == 0 :
        pass
    