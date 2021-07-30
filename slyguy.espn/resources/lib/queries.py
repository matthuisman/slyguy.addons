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
