from typing import NewType

# phone_id is the identifier of the phone number of the whatsapp account
WSPhoneID = NewType("WSPhoneID", str)
# business_id is the identifier of the whatsapp business account
WsBusinessID = NewType("WsBusinessID", str)
# The phone number of the customer
WhatsappPhone = NewType("WhatsappPhone", str)
# ID of the message
WhatsappMessageID = NewType("WhatsappMessageID", str)
