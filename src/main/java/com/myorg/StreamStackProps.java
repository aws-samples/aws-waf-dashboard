package com.myorg;

import software.amazon.awscdk.NestedStackProps;
import software.amazon.awscdk.services.opensearchservice.Domain;

public class StreamStackProps implements NestedStackProps {
    private final Domain openSearchDomain;

    public StreamStackProps(Domain openSearchDomain) {
        this.openSearchDomain = openSearchDomain;
    }

    public Domain getOpenSearchDomain() {
        return openSearchDomain;
    }
}
