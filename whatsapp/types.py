from typing import NewType

# phone_id is the identifier of the phone number of the whatsapp account
WSPhoneID = NewType("WSPhoneID", str)
# business_id is the identifier of the whatsapp business account
WsBusinessID = NewType("WsBusinessID", str)
# The phone number of the customer
WhatsappPhone = NewType("WhatsappPhone", str)
# The BSUID of the user
WhatsappBSUID = NewType("WhatsappBSUID", str)
# The username of the user
WhatsappUsername = NewType("WhatsappUsername", str)
# ID of the message
WhatsappMessageID = NewType("WhatsappMessageID", str)
# ID of the media
WhatsappMediaID = NewType("WhatsappMediaID", str)
