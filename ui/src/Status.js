import React, { Component } from 'react';
import Balance from './widgets/balance.js';
import Address from './widgets/address.js';
import Send from './widgets/send.js';
import EngineStatus from './widgets/engine.js';
import Authority from './widgets/authority.js';
import JobListing from './widgets/job_listing.js';

class Status extends Component {

  render() {
    return (
      <div className="container-fluid" style={{marginTop:16, marginBottom:64}}>
        <div className="row" style={{marginBottom:16}}>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <EngineStatus notify={this.props.notify} />
          </div>
        </div>
        <div className="row" style={{marginBottom:16}}>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <Authority 
              name="Can Alkan"
              description="Do my laundry"
              avatar="https://pbs.twimg.com/profile_images/723891323095388161/Oy-FbFUn_400x400.jpg"
              supply="125000"
              rewardPool="2000"
              rewardDistributed="24365"
            />
          </div>
        </div>
      </div>
    );
  }
}

export default Status;