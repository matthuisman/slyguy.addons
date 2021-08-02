WATCH = '''
query(
  $countryCode: String!,
  $deviceType: DeviceType!,
  $tz: String,
  $id: ID!,
  $packageId: String
) {
  airing(
    countryCode: $countryCode,
    deviceType: $deviceType,
    tz: $tz,
    id: $id
  ) {     id
airingId
simulcastAiringId
name
shortName
feedName
language
image {
  url
}
pickerImage: image(type: PICKER) {
  url
}description
type
startDateTime
endDateTime
originalAiringStartDateTime
source (authorization: SHIELD) {
  url
  authorizationType
  hasPassThroughAds
  hasNielsenWatermarks
  hasEspnId3Heartbeats
  commercialReplacement
}
network {
  id
  name
  type
}
sport {
  id
  uid
  name
  abbreviation
  code
}
league {
  id
  uid
  name
  abbreviation
  code
}
links {
  web
  mobileShare
}
program {
  id
  code
  categoryCode
  isStudio
}
tracking {
  trackingId
  nielsenCrossId1
  nielsenCrossId2
  comscoreC6
}
franchise {
  id 
  name 
}
authTypes
adobeRSS(packageId: $packageId)
duration
eventId
gameId
seekInSeconds
requiresLinearPlayback
tier
includeSponsor
firstPresented
purchaseImage {
  url 
}
brands {
  id 
  name 
  type 
}
packages {
  name
}  }
}
'''

EPG = '''query Airings ( $countryCode: String!, $deviceType: DeviceType!, $tz: String!, $type: AiringType, $categories: [String], $networks: [String], $packages: [String], $eventId: String, $packageId: String, $start: String, $end: String, $day: String, $limit: Int ) { airings( countryCode: $countryCode, deviceType: $deviceType, tz: $tz, type: $type, categories: $categories, networks: $networks, packages: $packages, eventId: $eventId, packageId: $packageId, start: $start, end: $end, day: $day, limit: $limit ) { id airingId simulcastAiringId name type startDateTime shortDate: startDate(style: SHORT) authTypes adobeRSS duration feedName purchaseImage { url } image { url } network { id type abbreviation name shortName adobeResource isIpAuth } source { url authorizationType hasPassThroughAds hasNielsenWatermarks hasEspnId3Heartbeats commercialReplacement } packages { name } category { id name } subcategory { id name } sport { id name abbreviation code } league { id name abbreviation code } franchise { id name } program { id code categoryCode isStudio } tracking { nielsenCrossId1 nielsenCrossId2 comscoreC6 trackingId } } }'''
