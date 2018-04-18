import React, { Component } from 'react';
import Authority from './widgets/authority.js';
import axios from 'axios';
import {Card, CardText} from 'material-ui/Card';

class Auths extends Component {

  constructor(props) {
    super(props);
    this.state = {
      authList: []
    }
  }

  componentDidMount() {
    this.update();
  }

  update = () => {
    axios.get('/subauths').then((response) => {
      this.setState({
        authList: response.data
      })
    });
  }

  render() {

    let content = <Card style={{margin:"32px"}}>
                    <CardText>
                      There are no authorities in your blockchain
                    </CardText>
                  </Card>;

    if(this.state.authList.length > 0) {
      content = Object.entries(this.state.authList).map((auth) => {
        auth = auth[1];
        return <div key={auth.name} className="col-lg-6 col-md-6 col-sm-6">
                <Authority 
                  name={auth.name}
                  description={auth.description}
                  avatar="https://pbs.twimg.com/profile_images/723891323095388161/Oy-FbFUn_400x400.jpg"
                  supply={auth.current_supply}
                  rewardPool={auth.available_reward}
                  rewardDistributed={auth.initial_supply - auth.current_supply}
                  webAddress={auth.host}
                />
              </div>
      });
    }

    return (
      <div className="container-fluid" style={{marginTop:16, marginBottom:64}}>
        <div className="row" style={{marginBottom:16}}>
          {content}
        </div>
      </div>
    );
  }
}

export default Auths;