PLAYBACK = '''{
    video(id: VIDEO_ID) {
        id
        type
        badge
        image
        primaryLabel
        secondaryLabel
        season
        episode
        captions
        synopsis
        rating {
            classification
            advisoryWarnings
        }
        analytics {
            showId
            videoId
            screenName
            pageType
        }
        schedule {
            windows  {
                from
                to
                state
            }
        }
        duration {
            total
            watched
        }
        playback {
            bcPayload
            live {
                url
                state
                dvrEnabled
            }
            youbora {
                title
                accountCode
                contentId
            }
            advertising {
                video {
                    ssaiParams
                    csaiAdServerUrl
                }
                onPause {
                    slotName
                    custParams
                    allowMultipleAop
                }
            }
        }
    }
}'''
