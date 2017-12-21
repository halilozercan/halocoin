import React, { Component } from 'react';
import Balance from './widgets/balance.js';
import Address from './widgets/address.js';
import Send from './widgets/send.js';
import Miner from './widgets/miner.js';
import Power from './widgets/power.js';
import JobListing from './widgets/job_listing.js';

class Mining extends Component {

  render() {
    return (
      <div className="container-fluid" style={{marginTop:16, marginBottom:64}}>
        <div className="row">
          <Miner />
        </div>
        <div className="row">
          <Power />
        </div>
        <div className="row">
          <JobListing />
        </div>
      </div>
    );
  }
}

export default Mining;