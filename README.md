# whereto-python-api
The repository which contains the back end API for WhereTo, a multi-platform mobile application allowing users to search parking rules in a given area.
## ParkAPI
 - Accepts float `radius` in miles and string `address`
 - Returns an object consisting of all detecting parking road signs and meters in the given area
## DetailAPI
- Accepts an int `detection_id ` 
- Returns data for requested `detection_id`, including string address and image data