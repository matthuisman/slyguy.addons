@AbstractC12353o(mo70092a = "/apps-api/{deviceType}/lists/favoriteshows/unique/{uniqueName}/item/add.json")
AbstractC9510g<ShowAddedEndpointResponse> addMyShow(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "uniqueName") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/preference/{preferenceContainer}/{preferenceType}/add.json")
AbstractC9510g<PreferedShowsResponse> addToThePreferencesList(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "preferenceContainer") String str2, @AbstractC12357s(mo70097a = "preferenceType") String str3, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str4);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/subscription/amazon/cancel.json")
AbstractC9510g<AmazonIAPRelatedServerResponse> amazonCancelReceiptServerRequest(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/subscription/amazon/purchase.json")
AbstractC9510g<AmazonIAPRelatedServerResponse> amazonPurchaseRequest(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12339a RequestBody requestBody, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/subscription/amazon/receipt.json")
AbstractC9510g<AmazonRVSServerResponse> amazonRVSServerRequest(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/subscription/amazon/product/migrate.json")
AbstractC9510g<AmazonIAPRelatedServerResponse> amazonSwitchProductServerRequest(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/amazon/device/restoration.json")
AbstractC9510g<AutoLoginServerResponse> amazonVerifyAutoLoginServerRequest(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/video/continuewatching/watch-history.json")
AbstractC9510g<HistoryResponse> continueWatching(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/mvpd/user/convert.json")
AbstractC9510g<MvpdAuthZResponse> convertMvpdAuthZ(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12349k(mo70089a = {"Content-Type: application/x-www-form-urlencoded;charset=UTF-8"})
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/useraccount/registration.json")
AbstractC9510g<CreateEndpointResponse> createAccountByEmail(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12339a RequestBody requestBody, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12353o(mo70092a = "/apps-api/{deviceType}/lists/favoriteshows/create.json")
AbstractC9510g<MyShowEndpointResponse> createMyShowsList(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12341c(mo70080a = "uniqueName") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/mvpd/auth/deauthorize/user.json")
AbstractC9510g<MvpdAuthZResponse> deauthorizeMvpdAuthZ(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/base/{downloadUrl}")
@AbstractC12361w
AbstractC9510g<ResponseBody> downloadBrandVideo(@AbstractC12357s(mo70097a = "downloadUrl", mo70098b = true) String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.1/{deviceType}/dynamicplay/show/{showId}.json")
AbstractC9510g<DynamicVideoResponse> dynamicPlayVideo(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12349k(mo70089a = {"Content-Type: application/x-www-form-urlencoded;charset=UTF-8"})
@AbstractC12353o(mo70092a = "/apps-api/{deviceType}/auth/useraccount/password/reset/request.json")
AbstractC9510g<CreateEndpointResponse> forgotPassword(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12339a RequestBody requestBody, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/login/device/autologin/token.json")
AbstractC9510g<AccountTokenResponse> getAccountToken(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/ott/auth/code.json")
AbstractC9510g<ActivationCodeResponse> getActivationCode(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/ott/auth/status.json")
AbstractC9510g<ActivationCodeStatusResponse> getActivationCodeStatus(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/irdeto-control/anonymous-session-token.json")
AbstractC9510g<DRMSessionEndpointResponse> getAnonymousDRMSession(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/app/status.json")
AbstractC9510g<C12403l<StatusEndpointResponse>> getAppStatus(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12358t(mo70099a = "osv") String str2, @AbstractC12358t(mo70099a = "hwv") String str3, @AbstractC12347i(mo70088a = "Cache-Control") String str4);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/brands/{brandSlug}.json")
AbstractC9510g<BrandResponse> getBrand(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "brandSlug") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/brands.json")
AbstractC9510g<BrandsResponse> getBrands(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/brands/{brandSlug}/AtoZ.json")
AbstractC9510g<BrandPageResponse> getBrandsAtoZContent(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "brandSlug") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/brands/{brandSlug}/trending.json")
AbstractC9510g<BrandPageResponse> getBrandsTrendingContent(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "brandSlug") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/continuousplay/shows/{showId}/content/{contentId}/nextEpisode.json")
AbstractC9510g<CPNextEpisodeResponse> getCPNextEpisode(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12357s(mo70097a = "contentId") String str3, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str4);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/continuousplay/hint/promoted.json")
AbstractC9510g<PromotedVideoEndCardResponse> getCPPromotedShowVideo(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/continuousplay/shows/{showId}/content/{contentId}/hint/relatedHistory.json")
AbstractC9510g<RelatedShowVideoEndCardResponse> getCPRelatedShowHistoryVideo(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12357s(mo70097a = "contentId") String str3, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str4);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/continuousplay/content/{contentId}/related.json")
AbstractC9510g<RelatedShowVideoEndCardResponse> getCPRelatedShowVideo(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "contentId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/multiChannel.json")
AbstractC9510g<MultiChannelGroupResponse> getCachedMultiChannelGroups(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/shows/{showId}/cast.json")
AbstractC9510g<CastEndpointResponse> getCastInfo(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/cbssports/events/proxy.json?match=guid%7CMl_8xlr__D9RFI3OY8uXQmUK8c_Dfj2o")
AbstractC9510g<CbsSportsChannelResponse> getCbsSportsChannel(@AbstractC12347i(mo70088a = "Cache-Control") String str, @AbstractC12357s(mo70097a = "deviceType") String str2, @AbstractC12358t(mo70099a = "device") String str3);

@AbstractC12344f(mo70083a = "apps-api/v3.0/{deviceType}/cbsn/schedule/feed.json")
AbstractC9510g<CbsnChannelResponse> getCbsnChannels(@AbstractC12347i(mo70088a = "Cache-Control") String str, @AbstractC12357s(mo70097a = "deviceType") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/live/channels/{channelSlug}/listings.json")
AbstractC9510g<ListingsEndpointResponse> getChannelListings(@AbstractC12357s(mo70097a = "channelSlug") String str, @AbstractC12357s(mo70097a = "deviceType") String str2, @AbstractC12359u Map<String, String> map, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/live/channels.json")
AbstractC9510g<ChannelsResponse> getChannels(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/device/cookie/migration/regenerate.json")
AbstractC9510g<AuthEndpointResponse> getCookieForRegeneration(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12358t(mo70099a = "token") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/device/cookie/migration/token.json")
AbstractC9510g<AccountTokenResponse> getCookieMigrationToken(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.1/{deviceType}/continuousplay/content/{contentId}/hint/amlg/showrecommendation.json")
AbstractC9510g<RelatedShowVideoEndCardResponse> getCpShowRecommendationMlVideos(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "contentId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/irdeto-control/session-token.json")
AbstractC9510g<DRMSessionEndpointResponse> getDRMSession(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/dma.json")
AbstractC9510g<DmaResponse> getDmas(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "apps-api/v3.0/{deviceType}/etl/liveschedule/feed.json")
AbstractC9510g<EtlChannelResponse> getEtlChannels(@AbstractC12347i(mo70088a = "Cache-Control") String str, @AbstractC12357s(mo70097a = "deviceType") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/shows/promo/featured.json")
AbstractC9510g<ShowsPromoFeaturedResponse> getFeaturedShows(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/video/signature/generate.json")
AbstractC9510g<GenerateEndpointResponse> getGenerated(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/preference/view.json")
@AbstractC12349k(mo70089a = {"preference-key:9eVbNQtBRjJnvRPL8vQnBOXzy88nZMLJ"})
AbstractC9510g<PreferedShowsResponse> getListOfPreferences(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/live/channels/listings/{listingId}.json")
AbstractC9510g<ListingDetailResponse> getListing(@AbstractC12357s(mo70097a = "listingId") String str, @AbstractC12357s(mo70097a = "deviceType") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/cbs/affiliate/{affiliateName}.json")
AbstractC9510g<AffiliateEndpointResponse> getLiveTvAffiliate(@AbstractC12357s(mo70097a = "affiliateName") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/login/status.json")
AbstractC9510g<AuthStatusEndpointResponse> getLoginStatus(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/home/marquee.json")
AbstractC9510g<MarqueeEndpointResponse> getMarquee(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/movies/{contentId}.json")
AbstractC9510g<MovieEndpointResponse> getMovie(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "contentId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/movies/trailer/{contentId}.json")
AbstractC9510g<MovieEndpointResponse> getMovieByTrailer(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "contentId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/movies/genre.json")
AbstractC9510g<MovieGenresEndpointResponse> getMovieGenres(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/movies.json")
AbstractC9510g<MoviesEndpointResponse> getMovies(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/movies.json")
AbstractC9510g<MoviesEndpointResponse> getMoviesByGenre(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/movies/trending.json")
AbstractC9510g<MoviesTrendingEndpointResponse> getMoviesTrending(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u Map<String, String> map, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/multiChannel.json")
AbstractC9510g<MultiChannelGroupResponse> getMultiChannelGroups(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/mvpd/configs.json")
AbstractC9510g<MVPDConfigsEndpointResponse> getMvpdConfigs(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/{deviceType}/lists/favoriteshows/unique/{uniqueName}.json")
AbstractC9510g<MyShowEndpointResponse> getMyShows(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "uniqueName") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/user/video/mycbs.json")
AbstractC9510g<MyVideoResponse> getMyVideos(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/news/hub/shows.json")
AbstractC9510g<NewsHubShowsResponse> getNewsHubShows(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/news/hub/stories.json")
AbstractC9510g<NewsHubStoriesResponse> getNewsHubStories(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/shows/{showId}/video/autoplay/nextEpisode.json")
AbstractC9510g<NextEpisodeResponse> getNextEpisode(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/schedule/{scheduleType}/feed.json")
AbstractC9510g<NonLocalChannelScheduleResponse> getNonLocalChannelScheduleResponse(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "scheduleType") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/user/variants.json")
AbstractC9510g<OptimizelyTestVariantsResponse> getOptimizelyTestVariants(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/pageAttribute.json")
AbstractC9510g<PageAttributeResponse> getPageAttributes(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/pageAttribute/tags/group.json")
AbstractC9510g<PageAttributeGroupResponse> getPageAttributesGroup(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/pageAttribute.json")
AbstractC9510g<NewPageAttributeResponse> getPageAttributesNew(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/shows/{showId}/related/shows.json")
AbstractC9510g<RelatedShowsEndpointResponse> getRelatedShows(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/ott/devices/{partner}/auth/activate.json")
AbstractC9510g<ActivateEndpointResponse> getRendezvousAuthorizeDevice(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "partner") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/schedule.json")
AbstractC9510g<ScheduleEndpointResponse> getSchedule(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/contentsearch/search.json")
AbstractC9510g<SearchContentResponse> getSearchContent(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/shows/{showId}.json")
AbstractC9510g<ShowEndpointResponse> getShow(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/shows/groups.json")
AbstractC9510g<ShowGroupResponse> getShowGroups(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, Boolean> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/video/show/{showId}/streams/history.json")
AbstractC9510g<HistoryResponse> getShowHistory(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/shows/{showId}/menu.json")
AbstractC9510g<ShowMenuResponse> getShowMenu(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/shows/slug/{showName}.json")
AbstractC9510g<ShowPageDataResponse> getShowPageData(@AbstractC12357s(mo70097a = "showName") String str, @AbstractC12357s(mo70097a = "deviceType") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/shows/{showId}/video/season/availability.json")
AbstractC9510g<ShowSeasonAvailabilityResponse> getShowSeasonAvailability(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/shows/video/{showId}.json")
AbstractC9510g<VideoEndpointResponse> getShowVideos(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/shows/group/{groupId}.json?")
AbstractC9510g<SingleShowGroupResponse> getShowsByGroupId(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "groupId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/home/configurator/shows.json")
AbstractC9510g<HomeCarouselContentSectionResponse> getShowsSection(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u Map<String, String> map, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/video/signature/individualize.json")
AbstractC9510g<IndividualizeEndpointResponse> getUniqueUser(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/upsell.json")
AbstractC9510g<UpsellEndpointResponse> getUpsellInfo(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/video/streams/history.json")
AbstractC9510g<HistoryResponse> getUserHistory(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/episode/{showId}/{seasonNumber}/{episodeNumber}.json")
AbstractC9510g<VideoSeasonEpisodeEndpointResponse> getVideoBySeasonAndEpisode(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12357s(mo70097a = "seasonNumber") String str3, @AbstractC12357s(mo70097a = "episodeNumber") String str4, @AbstractC12347i(mo70088a = "Cache-Control") String str5);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/shows/{showId}/videos/config/{uniqueName}.json")
AbstractC9510g<VideoConfigResponse> getVideoConfig(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "showId") String str2, @AbstractC12357s(mo70097a = "uniqueName") String str3, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str4);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/videos/section/{sectionId}.json")
AbstractC9510g<VideoConfigSectionResponse> getVideoConfigSection(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "sectionId") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/video/cid/{contentId}.json")
AbstractC9510g<VideoEndpointResponse> getVideoData(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "contentId") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/video/streams.json")
AbstractC9510g<VideoStreamsEndpoint> getVideoStream(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/googleplay/device/restoration.json")
AbstractC9510g<AutoLoginServerResponse> googlePlayVerifyAutoLoginServerRequest(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/home/configurator.json")
AbstractC9510g<HomeCarouselConfigResponse> homeCarouselConfig(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api{path}")
AbstractC9510g<HomeCarouselContentSectionResponse> homeCarouselContentSection(@AbstractC12357s(mo70097a = "path", mo70098b = true) String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api{path}")
AbstractC9510g<HomeCarouselCWSectionResponse> homeCarouselContinueWatchingSection(@AbstractC12357s(mo70097a = "path", mo70098b = true) String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api{path}")
AbstractC9510g<HomeCarouselKWSectionResponse> homeCarouselKeepWatchingSection(@AbstractC12357s(mo70097a = "path", mo70098b = true) String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api{path}")
AbstractC9510g<HomeShowGroupConfigResponse> homeCarouselShowGroupConfig(@AbstractC12357s(mo70097a = "path", mo70098b = true) String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api{path}")
AbstractC9510g<HomeCarouselVideoConfigSectionResponse> homeCarouselVideoConfigSection(@AbstractC12357s(mo70097a = "path", mo70098b = true) String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/{uniqueName}.json")
AbstractC9510g<HomeShowGroupConfigResponse> homeShowConfig(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "uniqueName") String str2, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/homeshowgroup.json")
AbstractC9510g<HomeShowGroupConfigResponse> homeShowGroupConfig(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/homeshowgroup/{homeShowGroupSectionId}.json")
AbstractC9510g<SingleHomeShowGroupResponse> homeShowGroupSectionConfig(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "homeShowGroupSectionId") long j, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.1/{deviceType}/video/keepwatching/watch-history.json")
AbstractC9510g<KeepWatchingResponse> keepWatching(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps/user/ip.json")
AbstractC9510g<UserIpLookupResponse> lookUpUserIp(@AbstractC12347i(mo70088a = "Cache-Control") String str);

@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/recommendation/amlg/shows/showpicker.json")
AbstractC9510g<RecommendationResponse> postChosenTrendingShows(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12349k(mo70089a = {"Content-Type: application/x-www-form-urlencoded;charset=UTF-8"})
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/auth/login.json")
AbstractC9510g<AuthEndpointResponse> postLogin(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12339a RequestBody requestBody, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/recommendation/amlg/shows/variant.json")
AbstractC9510g<RecommendationResponse> recommendationForYou(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v3.0/{deviceType}/preference/{preferenceContainer}/{preferenceType}/remove.json")
AbstractC9510g<PreferedShowsResponse> removeFromThePreferencesList(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "preferenceContainer") String str2, @AbstractC12357s(mo70097a = "preferenceType") String str3, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str4);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/{deviceType}/lists/favoriteshows/unique/{uniqueName}/item/delete.json")
AbstractC9510g<ShowAddedEndpointResponse> removeMyShow(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12357s(mo70097a = "uniqueName") String str2, @AbstractC12341c(mo70080a = "showId") String str3, @AbstractC12347i(mo70088a = "Cache-Control") String str4);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/{deviceType}/video/show/history.json")
AbstractC9510g<ShowsYouWatchResponse> showsYouWatch(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/googleplay/switchProduct.json")
AbstractC9510g<PlayBillingResponse> switchProduct(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/mvpd/auth/user/unbind.json")
AbstractC9510g<MvpdAuthZResponse> unbindMvpdAuthZ(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/mvpd/auth/user/unbind.json")
AbstractC9510g<MvpdAuthZResponse> unbindMvpdAuthZNoParam(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12339a RequestBody requestBody, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/useraccount/settings.json")
AbstractC9510g<UpdateProfileEndpointResponse> updatePersonalIdentifiableInfo(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/googleplay/purchase.json")
AbstractC9510g<PlayBillingResponse> verifyGooglePlayBillingPurchase(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12339a RequestBody requestBody, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v3.0/{deviceType}/mvpd/adobe/shortMediaToken.json")
AbstractC9510g<MvpdEndpointResponse> verifyMpvdToken(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12341c(mo70080a = "token") String str2, @AbstractC12347i(mo70088a = "Cache-Control") String str3);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/mvpd/auth/user.json")
AbstractC9510g<MvpdAuthZResponse> verifyMvpdAnonAuthZ(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/mvpd/auth/bind/user.json")
AbstractC9510g<MvpdAuthZResponse> verifyMvpdRegAuthZ(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);

@AbstractC12344f(mo70083a = "/apps-api/v2.0/zipcode/check.json")
AbstractC9510g<PostalCodeResponse> verifyPostalCode(@AbstractC12359u HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str);

@AbstractC12343e
@AbstractC12353o(mo70092a = "/apps-api/v2.0/{deviceType}/googleplay/verify/token.json")
AbstractC9510g<PlayBillingTokenVerifyResponse> verifyToken(@AbstractC12357s(mo70097a = "deviceType") String str, @AbstractC12342d HashMap<String, String> hashMap, @AbstractC12347i(mo70088a = "Cache-Control") String str2);